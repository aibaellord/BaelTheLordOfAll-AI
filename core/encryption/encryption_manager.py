#!/usr/bin/env python3
"""
BAEL - Encryption Manager
Comprehensive encryption and cryptographic services.

This module provides a complete encryption framework
for secure data protection and cryptographic operations.

Features:
- Symmetric encryption (AES)
- Asymmetric encryption (RSA simulation)
- Hashing (SHA, Blake2)
- Key derivation (PBKDF2, Scrypt)
- Digital signatures
- Secure random generation
- Key management
- Envelope encryption
- Password hashing
- Token generation
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import struct
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class EncryptionAlgorithm(Enum):
    """Encryption algorithms."""
    AES_128_CBC = "aes-128-cbc"
    AES_256_CBC = "aes-256-cbc"
    AES_128_GCM = "aes-128-gcm"
    AES_256_GCM = "aes-256-gcm"
    CHACHA20 = "chacha20"
    XOR = "xor"  # Simple fallback


class HashAlgorithm(Enum):
    """Hashing algorithms."""
    SHA256 = "sha256"
    SHA384 = "sha384"
    SHA512 = "sha512"
    SHA3_256 = "sha3_256"
    SHA3_512 = "sha3_512"
    BLAKE2B = "blake2b"
    BLAKE2S = "blake2s"
    MD5 = "md5"  # Legacy only


class KeyDerivationAlgorithm(Enum):
    """Key derivation algorithms."""
    PBKDF2 = "pbkdf2"
    SCRYPT = "scrypt"
    ARGON2 = "argon2"
    HKDF = "hkdf"


class KeyType(Enum):
    """Key types."""
    SYMMETRIC = "symmetric"
    PUBLIC = "public"
    PRIVATE = "private"
    MASTER = "master"
    DERIVED = "derived"


class EncodingFormat(Enum):
    """Encoding formats."""
    BASE64 = "base64"
    HEX = "hex"
    RAW = "raw"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class CryptoKey:
    """Cryptographic key."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    key_data: bytes = b""
    key_type: KeyType = KeyType.SYMMETRIC
    algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_CBC

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    rotated_from: Optional[str] = None

    # Usage tracking
    encryption_count: int = 0
    decryption_count: int = 0

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    @property
    def key_size(self) -> int:
        return len(self.key_data) * 8  # bits


@dataclass
class EncryptedData:
    """Encrypted data container."""
    ciphertext: bytes
    iv: bytes = b""
    tag: bytes = b""  # For authenticated encryption
    algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_CBC
    key_id: str = ""

    def to_bytes(self) -> bytes:
        """Serialize to bytes."""
        # Format: iv_len(2) + iv + tag_len(2) + tag + ciphertext
        data = struct.pack('>H', len(self.iv)) + self.iv
        data += struct.pack('>H', len(self.tag)) + self.tag
        data += self.ciphertext
        return data

    @classmethod
    def from_bytes(cls, data: bytes) -> 'EncryptedData':
        """Deserialize from bytes."""
        offset = 0

        iv_len = struct.unpack('>H', data[offset:offset + 2])[0]
        offset += 2
        iv = data[offset:offset + iv_len]
        offset += iv_len

        tag_len = struct.unpack('>H', data[offset:offset + 2])[0]
        offset += 2
        tag = data[offset:offset + tag_len]
        offset += tag_len

        ciphertext = data[offset:]

        return cls(ciphertext=ciphertext, iv=iv, tag=tag)

    def to_base64(self) -> str:
        """Encode to base64 string."""
        return base64.b64encode(self.to_bytes()).decode('ascii')

    @classmethod
    def from_base64(cls, s: str) -> 'EncryptedData':
        """Decode from base64 string."""
        return cls.from_bytes(base64.b64decode(s))


@dataclass
class PasswordHash:
    """Password hash result."""
    hash: bytes
    salt: bytes
    algorithm: KeyDerivationAlgorithm
    iterations: int = 100000

    def to_string(self) -> str:
        """Convert to storable string."""
        return (
            f"${self.algorithm.value}${self.iterations}$"
            f"{base64.b64encode(self.salt).decode()}$"
            f"{base64.b64encode(self.hash).decode()}"
        )

    @classmethod
    def from_string(cls, s: str) -> 'PasswordHash':
        """Parse from stored string."""
        parts = s.split('$')
        if len(parts) != 5:
            raise ValueError("Invalid hash format")

        _, algorithm, iterations, salt_b64, hash_b64 = parts

        return cls(
            hash=base64.b64decode(hash_b64),
            salt=base64.b64decode(salt_b64),
            algorithm=KeyDerivationAlgorithm(algorithm),
            iterations=int(iterations)
        )


@dataclass
class Signature:
    """Digital signature."""
    signature: bytes
    algorithm: HashAlgorithm = HashAlgorithm.SHA256
    key_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_base64(self) -> str:
        return base64.b64encode(self.signature).decode('ascii')


# =============================================================================
# CIPHER IMPLEMENTATIONS
# =============================================================================

class Cipher(ABC):
    """Abstract cipher interface."""

    @abstractmethod
    def encrypt(self, data: bytes, key: bytes, iv: bytes = None) -> EncryptedData:
        """Encrypt data."""
        pass

    @abstractmethod
    def decrypt(self, encrypted: EncryptedData, key: bytes) -> bytes:
        """Decrypt data."""
        pass


class XORCipher(Cipher):
    """Simple XOR cipher (fallback when no crypto library available)."""

    def encrypt(self, data: bytes, key: bytes, iv: bytes = None) -> EncryptedData:
        iv = iv or os.urandom(16)

        # Derive key stream from key + iv
        key_stream = self._derive_key_stream(key, iv, len(data))

        ciphertext = bytes(d ^ k for d, k in zip(data, key_stream))

        # Simple MAC
        tag = hmac.new(key, iv + ciphertext, hashlib.sha256).digest()[:16]

        return EncryptedData(
            ciphertext=ciphertext,
            iv=iv,
            tag=tag,
            algorithm=EncryptionAlgorithm.XOR
        )

    def decrypt(self, encrypted: EncryptedData, key: bytes) -> bytes:
        # Verify MAC
        expected_tag = hmac.new(
            key, encrypted.iv + encrypted.ciphertext, hashlib.sha256
        ).digest()[:16]

        if not hmac.compare_digest(expected_tag, encrypted.tag):
            raise ValueError("Authentication failed")

        key_stream = self._derive_key_stream(
            key, encrypted.iv, len(encrypted.ciphertext)
        )

        return bytes(c ^ k for c, k in zip(encrypted.ciphertext, key_stream))

    def _derive_key_stream(self, key: bytes, iv: bytes, length: int) -> bytes:
        """Derive key stream using HMAC-based expansion."""
        stream = b""
        counter = 0

        while len(stream) < length:
            block = hmac.new(
                key,
                iv + struct.pack('>I', counter),
                hashlib.sha256
            ).digest()
            stream += block
            counter += 1

        return stream[:length]


class AESCipher(Cipher):
    """AES cipher implementation."""

    def __init__(self, mode: str = "cbc", key_size: int = 256):
        self.mode = mode
        self.key_size = key_size
        self._fallback = XORCipher()

    def encrypt(self, data: bytes, key: bytes, iv: bytes = None) -> EncryptedData:
        try:
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import padding
            from cryptography.hazmat.primitives.ciphers import (Cipher,
                                                                algorithms,
                                                                modes)

            iv = iv or os.urandom(16)

            if self.mode == "gcm":
                cipher = Cipher(
                    algorithms.AES(key),
                    modes.GCM(iv),
                    backend=default_backend()
                )
                encryptor = cipher.encryptor()
                ciphertext = encryptor.update(data) + encryptor.finalize()

                return EncryptedData(
                    ciphertext=ciphertext,
                    iv=iv,
                    tag=encryptor.tag,
                    algorithm=EncryptionAlgorithm.AES_256_GCM
                )
            else:
                # CBC mode
                padder = padding.PKCS7(128).padder()
                padded_data = padder.update(data) + padder.finalize()

                cipher = Cipher(
                    algorithms.AES(key),
                    modes.CBC(iv),
                    backend=default_backend()
                )
                encryptor = cipher.encryptor()
                ciphertext = encryptor.update(padded_data) + encryptor.finalize()

                # MAC for CBC
                tag = hmac.new(key, iv + ciphertext, hashlib.sha256).digest()[:16]

                return EncryptedData(
                    ciphertext=ciphertext,
                    iv=iv,
                    tag=tag,
                    algorithm=EncryptionAlgorithm.AES_256_CBC
                )

        except ImportError:
            # Fallback to XOR cipher
            return self._fallback.encrypt(data, key, iv)

    def decrypt(self, encrypted: EncryptedData, key: bytes) -> bytes:
        try:
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import padding
            from cryptography.hazmat.primitives.ciphers import (Cipher,
                                                                algorithms,
                                                                modes)

            if self.mode == "gcm":
                cipher = Cipher(
                    algorithms.AES(key),
                    modes.GCM(encrypted.iv, encrypted.tag),
                    backend=default_backend()
                )
                decryptor = cipher.decryptor()
                return decryptor.update(encrypted.ciphertext) + decryptor.finalize()
            else:
                # Verify MAC
                expected_tag = hmac.new(
                    key, encrypted.iv + encrypted.ciphertext, hashlib.sha256
                ).digest()[:16]

                if not hmac.compare_digest(expected_tag, encrypted.tag):
                    raise ValueError("Authentication failed")

                cipher = Cipher(
                    algorithms.AES(key),
                    modes.CBC(encrypted.iv),
                    backend=default_backend()
                )
                decryptor = cipher.decryptor()
                padded = decryptor.update(encrypted.ciphertext) + decryptor.finalize()

                unpadder = padding.PKCS7(128).unpadder()
                return unpadder.update(padded) + unpadder.finalize()

        except ImportError:
            return self._fallback.decrypt(encrypted, key)


# =============================================================================
# HASHER
# =============================================================================

class Hasher:
    """Hashing utility."""

    @staticmethod
    def hash(data: bytes, algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> bytes:
        """Hash data."""
        if algorithm == HashAlgorithm.SHA256:
            return hashlib.sha256(data).digest()
        elif algorithm == HashAlgorithm.SHA384:
            return hashlib.sha384(data).digest()
        elif algorithm == HashAlgorithm.SHA512:
            return hashlib.sha512(data).digest()
        elif algorithm == HashAlgorithm.SHA3_256:
            return hashlib.sha3_256(data).digest()
        elif algorithm == HashAlgorithm.SHA3_512:
            return hashlib.sha3_512(data).digest()
        elif algorithm == HashAlgorithm.BLAKE2B:
            return hashlib.blake2b(data).digest()
        elif algorithm == HashAlgorithm.BLAKE2S:
            return hashlib.blake2s(data).digest()
        elif algorithm == HashAlgorithm.MD5:
            return hashlib.md5(data).digest()
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

    @staticmethod
    def hash_string(s: str, algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> str:
        """Hash string and return hex."""
        return Hasher.hash(s.encode('utf-8'), algorithm).hex()

    @staticmethod
    def verify(data: bytes, expected_hash: bytes, algorithm: HashAlgorithm) -> bool:
        """Verify hash."""
        actual = Hasher.hash(data, algorithm)
        return hmac.compare_digest(actual, expected_hash)


# =============================================================================
# KEY DERIVATION
# =============================================================================

class KeyDerivation:
    """Key derivation functions."""

    @staticmethod
    def derive_key(
        password: bytes,
        salt: bytes,
        length: int = 32,
        algorithm: KeyDerivationAlgorithm = KeyDerivationAlgorithm.PBKDF2,
        iterations: int = 100000
    ) -> bytes:
        """Derive key from password."""
        if algorithm == KeyDerivationAlgorithm.PBKDF2:
            return hashlib.pbkdf2_hmac(
                'sha256', password, salt, iterations, dklen=length
            )

        elif algorithm == KeyDerivationAlgorithm.SCRYPT:
            try:
                return hashlib.scrypt(
                    password, salt=salt, n=16384, r=8, p=1, dklen=length
                )
            except:
                # Fallback to PBKDF2
                return hashlib.pbkdf2_hmac(
                    'sha256', password, salt, iterations, dklen=length
                )

        elif algorithm == KeyDerivationAlgorithm.HKDF:
            # Simple HKDF implementation
            prk = hmac.new(salt, password, hashlib.sha256).digest()

            result = b""
            prev = b""
            counter = 1

            while len(result) < length:
                data = prev + bytes([counter])
                prev = hmac.new(prk, data, hashlib.sha256).digest()
                result += prev
                counter += 1

            return result[:length]

        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")


# =============================================================================
# PASSWORD HASHER
# =============================================================================

class PasswordHasher:
    """Secure password hashing."""

    def __init__(
        self,
        algorithm: KeyDerivationAlgorithm = KeyDerivationAlgorithm.PBKDF2,
        iterations: int = 100000,
        salt_length: int = 32,
        hash_length: int = 32
    ):
        self.algorithm = algorithm
        self.iterations = iterations
        self.salt_length = salt_length
        self.hash_length = hash_length

    def hash(self, password: str) -> PasswordHash:
        """Hash a password."""
        salt = os.urandom(self.salt_length)

        hash_bytes = KeyDerivation.derive_key(
            password.encode('utf-8'),
            salt,
            self.hash_length,
            self.algorithm,
            self.iterations
        )

        return PasswordHash(
            hash=hash_bytes,
            salt=salt,
            algorithm=self.algorithm,
            iterations=self.iterations
        )

    def verify(self, password: str, password_hash: PasswordHash) -> bool:
        """Verify password against hash."""
        test_hash = KeyDerivation.derive_key(
            password.encode('utf-8'),
            password_hash.salt,
            len(password_hash.hash),
            password_hash.algorithm,
            password_hash.iterations
        )

        return hmac.compare_digest(test_hash, password_hash.hash)

    def needs_rehash(self, password_hash: PasswordHash) -> bool:
        """Check if hash needs to be updated."""
        return (
            password_hash.algorithm != self.algorithm or
            password_hash.iterations < self.iterations
        )


# =============================================================================
# TOKEN GENERATOR
# =============================================================================

class TokenGenerator:
    """Secure token generation."""

    @staticmethod
    def generate_token(length: int = 32, encoding: EncodingFormat = EncodingFormat.HEX) -> str:
        """Generate a random token."""
        raw = secrets.token_bytes(length)

        if encoding == EncodingFormat.HEX:
            return raw.hex()
        elif encoding == EncodingFormat.BASE64:
            return base64.urlsafe_b64encode(raw).decode('ascii')
        else:
            return raw.hex()

    @staticmethod
    def generate_api_key(prefix: str = "bael") -> str:
        """Generate an API key."""
        random_part = secrets.token_urlsafe(24)
        checksum = hashlib.sha256(random_part.encode()).hexdigest()[:6]
        return f"{prefix}_{random_part}_{checksum}"

    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """Generate OTP code."""
        return ''.join(str(secrets.randbelow(10)) for _ in range(length))

    @staticmethod
    def generate_uuid() -> str:
        """Generate UUID v4."""
        return str(uuid.uuid4())


# =============================================================================
# KEY MANAGER
# =============================================================================

class KeyManager:
    """Cryptographic key management."""

    def __init__(self):
        self.keys: Dict[str, CryptoKey] = {}
        self.key_aliases: Dict[str, str] = {}
        self.master_key: Optional[bytes] = None

    def set_master_key(self, key: bytes) -> None:
        """Set the master key for key encryption."""
        if len(key) != 32:
            raise ValueError("Master key must be 32 bytes")
        self.master_key = key

    def derive_master_key(self, password: str, salt: bytes = None) -> bytes:
        """Derive master key from password."""
        salt = salt or os.urandom(32)
        self.master_key = KeyDerivation.derive_key(
            password.encode('utf-8'),
            salt,
            32,
            KeyDerivationAlgorithm.SCRYPT
        )
        return self.master_key

    def generate_key(
        self,
        key_type: KeyType = KeyType.SYMMETRIC,
        algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_CBC,
        expires_in: timedelta = None
    ) -> CryptoKey:
        """Generate a new key."""
        # Determine key size
        key_size = 32  # 256 bits
        if "128" in algorithm.value:
            key_size = 16

        key_data = os.urandom(key_size)

        key = CryptoKey(
            key_data=key_data,
            key_type=key_type,
            algorithm=algorithm,
            expires_at=datetime.now() + expires_in if expires_in else None
        )

        self.keys[key.id] = key
        return key

    def get_key(self, key_id: str) -> Optional[CryptoKey]:
        """Get a key by ID."""
        # Check aliases
        if key_id in self.key_aliases:
            key_id = self.key_aliases[key_id]

        return self.keys.get(key_id)

    def set_alias(self, alias: str, key_id: str) -> None:
        """Set an alias for a key."""
        if key_id not in self.keys:
            raise ValueError(f"Key not found: {key_id}")
        self.key_aliases[alias] = key_id

    def rotate_key(self, old_key_id: str) -> CryptoKey:
        """Rotate a key."""
        old_key = self.get_key(old_key_id)
        if not old_key:
            raise ValueError(f"Key not found: {old_key_id}")

        new_key = self.generate_key(
            old_key.key_type,
            old_key.algorithm
        )
        new_key.rotated_from = old_key_id

        return new_key

    def delete_key(self, key_id: str) -> bool:
        """Delete a key."""
        if key_id in self.keys:
            del self.keys[key_id]
            return True
        return False

    def list_keys(self, include_expired: bool = False) -> List[str]:
        """List all key IDs."""
        if include_expired:
            return list(self.keys.keys())

        return [
            kid for kid, key in self.keys.items()
            if not key.is_expired
        ]


# =============================================================================
# ENCRYPTION MANAGER
# =============================================================================

class EncryptionManager:
    """
    Master encryption management for BAEL.

    Provides comprehensive cryptographic services.
    """

    def __init__(self):
        self.key_manager = KeyManager()
        self.password_hasher = PasswordHasher()
        self.token_generator = TokenGenerator()
        self.hasher = Hasher()

        # Ciphers
        self.ciphers: Dict[EncryptionAlgorithm, Cipher] = {
            EncryptionAlgorithm.AES_256_CBC: AESCipher("cbc", 256),
            EncryptionAlgorithm.AES_256_GCM: AESCipher("gcm", 256),
            EncryptionAlgorithm.AES_128_CBC: AESCipher("cbc", 128),
            EncryptionAlgorithm.XOR: XORCipher()
        }

        # Statistics
        self.encryptions = 0
        self.decryptions = 0
        self.hashes = 0

    # Key Management
    def generate_key(
        self,
        algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_CBC,
        alias: str = None,
        expires_in: timedelta = None
    ) -> CryptoKey:
        """Generate a new encryption key."""
        key = self.key_manager.generate_key(
            KeyType.SYMMETRIC, algorithm, expires_in
        )

        if alias:
            self.key_manager.set_alias(alias, key.id)

        return key

    def get_key(self, key_id: str) -> Optional[CryptoKey]:
        """Get a key."""
        return self.key_manager.get_key(key_id)

    # Encryption
    def encrypt(
        self,
        data: bytes,
        key: Union[str, bytes, CryptoKey],
        algorithm: EncryptionAlgorithm = None
    ) -> EncryptedData:
        """Encrypt data."""
        # Resolve key
        if isinstance(key, str):
            crypto_key = self.key_manager.get_key(key)
            if not crypto_key:
                raise ValueError(f"Key not found: {key}")
            key_bytes = crypto_key.key_data
            algorithm = algorithm or crypto_key.algorithm
            key_id = crypto_key.id
            crypto_key.encryption_count += 1
        elif isinstance(key, CryptoKey):
            key_bytes = key.key_data
            algorithm = algorithm or key.algorithm
            key_id = key.id
            key.encryption_count += 1
        else:
            key_bytes = key
            key_id = ""

        algorithm = algorithm or EncryptionAlgorithm.AES_256_CBC

        cipher = self.ciphers.get(algorithm)
        if not cipher:
            cipher = self.ciphers[EncryptionAlgorithm.XOR]

        encrypted = cipher.encrypt(data, key_bytes)
        encrypted.key_id = key_id
        encrypted.algorithm = algorithm

        self.encryptions += 1
        return encrypted

    def decrypt(
        self,
        encrypted: EncryptedData,
        key: Union[str, bytes, CryptoKey] = None
    ) -> bytes:
        """Decrypt data."""
        # Resolve key
        if key is None and encrypted.key_id:
            key = encrypted.key_id

        if isinstance(key, str):
            crypto_key = self.key_manager.get_key(key)
            if not crypto_key:
                raise ValueError(f"Key not found: {key}")
            key_bytes = crypto_key.key_data
            crypto_key.decryption_count += 1
        elif isinstance(key, CryptoKey):
            key_bytes = key.key_data
            key.decryption_count += 1
        else:
            key_bytes = key

        cipher = self.ciphers.get(encrypted.algorithm)
        if not cipher:
            cipher = self.ciphers[EncryptionAlgorithm.XOR]

        self.decryptions += 1
        return cipher.decrypt(encrypted, key_bytes)

    def encrypt_string(
        self,
        text: str,
        key: Union[str, bytes, CryptoKey],
        encoding: str = 'utf-8'
    ) -> str:
        """Encrypt string and return base64."""
        encrypted = self.encrypt(text.encode(encoding), key)
        return encrypted.to_base64()

    def decrypt_string(
        self,
        encrypted_base64: str,
        key: Union[str, bytes, CryptoKey],
        encoding: str = 'utf-8'
    ) -> str:
        """Decrypt base64 string."""
        encrypted = EncryptedData.from_base64(encrypted_base64)
        data = self.decrypt(encrypted, key)
        return data.decode(encoding)

    # Envelope Encryption
    def envelope_encrypt(
        self,
        data: bytes,
        master_key_id: str
    ) -> Tuple[EncryptedData, EncryptedData]:
        """Encrypt with envelope encryption (data key wrapped by master key)."""
        # Generate data key
        data_key = self.generate_key()

        # Encrypt data with data key
        encrypted_data = self.encrypt(data, data_key)

        # Encrypt data key with master key
        encrypted_key = self.encrypt(
            data_key.key_data,
            master_key_id
        )

        # Delete data key from memory
        self.key_manager.delete_key(data_key.id)

        return encrypted_data, encrypted_key

    def envelope_decrypt(
        self,
        encrypted_data: EncryptedData,
        encrypted_key: EncryptedData,
        master_key_id: str
    ) -> bytes:
        """Decrypt envelope encrypted data."""
        # Decrypt data key
        data_key_bytes = self.decrypt(encrypted_key, master_key_id)

        # Decrypt data
        return self.decrypt(encrypted_data, data_key_bytes)

    # Hashing
    def hash(
        self,
        data: bytes,
        algorithm: HashAlgorithm = HashAlgorithm.SHA256
    ) -> bytes:
        """Hash data."""
        self.hashes += 1
        return self.hasher.hash(data, algorithm)

    def hash_string(
        self,
        s: str,
        algorithm: HashAlgorithm = HashAlgorithm.SHA256
    ) -> str:
        """Hash string and return hex."""
        self.hashes += 1
        return self.hasher.hash_string(s, algorithm)

    # Signing
    def sign(
        self,
        data: bytes,
        key: Union[str, bytes, CryptoKey],
        algorithm: HashAlgorithm = HashAlgorithm.SHA256
    ) -> Signature:
        """Create HMAC signature."""
        if isinstance(key, str):
            crypto_key = self.key_manager.get_key(key)
            key_bytes = crypto_key.key_data
            key_id = crypto_key.id
        elif isinstance(key, CryptoKey):
            key_bytes = key.key_data
            key_id = key.id
        else:
            key_bytes = key
            key_id = ""

        sig_bytes = hmac.new(key_bytes, data, algorithm.value).digest()

        return Signature(
            signature=sig_bytes,
            algorithm=algorithm,
            key_id=key_id
        )

    def verify_signature(
        self,
        data: bytes,
        signature: Signature,
        key: Union[str, bytes, CryptoKey] = None
    ) -> bool:
        """Verify HMAC signature."""
        if key is None and signature.key_id:
            key = signature.key_id

        if isinstance(key, str):
            crypto_key = self.key_manager.get_key(key)
            key_bytes = crypto_key.key_data
        elif isinstance(key, CryptoKey):
            key_bytes = key.key_data
        else:
            key_bytes = key

        expected = hmac.new(
            key_bytes, data, signature.algorithm.value
        ).digest()

        return hmac.compare_digest(expected, signature.signature)

    # Password hashing
    def hash_password(self, password: str) -> str:
        """Hash a password."""
        ph = self.password_hasher.hash(password)
        return ph.to_string()

    def verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password."""
        ph = PasswordHash.from_string(stored_hash)
        return self.password_hasher.verify(password, ph)

    # Token generation
    def generate_token(self, length: int = 32) -> str:
        """Generate secure token."""
        return self.token_generator.generate_token(length)

    def generate_api_key(self, prefix: str = "bael") -> str:
        """Generate API key."""
        return self.token_generator.generate_api_key(prefix)

    def generate_otp(self, length: int = 6) -> str:
        """Generate OTP."""
        return self.token_generator.generate_otp(length)

    # Statistics
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            "encryptions": self.encryptions,
            "decryptions": self.decryptions,
            "hashes": self.hashes,
            "keys_stored": len(self.key_manager.keys),
            "key_aliases": len(self.key_manager.key_aliases)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Encryption System."""
    print("=" * 70)
    print("BAEL - ENCRYPTION MANAGER DEMO")
    print("Comprehensive Cryptographic Services")
    print("=" * 70)
    print()

    manager = EncryptionManager()

    # 1. Key Generation
    print("1. KEY GENERATION:")
    print("-" * 40)

    key = manager.generate_key(alias="main")
    print(f"   Key ID: {key.id[:16]}...")
    print(f"   Key size: {key.key_size} bits")
    print(f"   Algorithm: {key.algorithm.value}")
    print()

    # 2. Symmetric Encryption
    print("2. SYMMETRIC ENCRYPTION:")
    print("-" * 40)

    plaintext = b"BAEL - The Lord of All AI Agents"
    encrypted = manager.encrypt(plaintext, "main")

    print(f"   Plaintext: {plaintext.decode()}")
    print(f"   Encrypted size: {len(encrypted.ciphertext)} bytes")
    print(f"   IV: {encrypted.iv.hex()[:32]}...")

    decrypted = manager.decrypt(encrypted)
    print(f"   Decrypted: {decrypted.decode()}")
    print()

    # 3. String Encryption
    print("3. STRING ENCRYPTION:")
    print("-" * 40)

    secret = "Sensitive data here"
    encrypted_str = manager.encrypt_string(secret, "main")
    print(f"   Original: {secret}")
    print(f"   Encrypted: {encrypted_str[:50]}...")

    decrypted_str = manager.decrypt_string(encrypted_str, "main")
    print(f"   Decrypted: {decrypted_str}")
    print()

    # 4. Hashing
    print("4. HASHING:")
    print("-" * 40)

    data = b"Hash this data"

    sha256 = manager.hash_string("Hello World", HashAlgorithm.SHA256)
    print(f"   SHA256: {sha256[:32]}...")

    sha512 = manager.hash_string("Hello World", HashAlgorithm.SHA512)
    print(f"   SHA512: {sha512[:32]}...")

    blake2 = manager.hash_string("Hello World", HashAlgorithm.BLAKE2B)
    print(f"   BLAKE2B: {blake2[:32]}...")
    print()

    # 5. Password Hashing
    print("5. PASSWORD HASHING:")
    print("-" * 40)

    password = "SecureP@ssw0rd!"
    hashed = manager.hash_password(password)
    print(f"   Password: {password}")
    print(f"   Hash: {hashed[:50]}...")

    valid = manager.verify_password(password, hashed)
    invalid = manager.verify_password("wrong", hashed)
    print(f"   Correct password: {valid}")
    print(f"   Wrong password: {invalid}")
    print()

    # 6. Token Generation
    print("6. TOKEN GENERATION:")
    print("-" * 40)

    token = manager.generate_token(32)
    print(f"   Random token: {token}")

    api_key = manager.generate_api_key("bael")
    print(f"   API key: {api_key}")

    otp = manager.generate_otp(6)
    print(f"   OTP: {otp}")
    print()

    # 7. Digital Signatures
    print("7. DIGITAL SIGNATURES:")
    print("-" * 40)

    message = b"Sign this message"
    signature = manager.sign(message, "main")

    print(f"   Message: {message.decode()}")
    print(f"   Signature: {signature.to_base64()[:40]}...")

    valid = manager.verify_signature(message, signature)
    print(f"   Signature valid: {valid}")

    invalid = manager.verify_signature(b"tampered", signature)
    print(f"   Tampered message: {invalid}")
    print()

    # 8. Envelope Encryption
    print("8. ENVELOPE ENCRYPTION:")
    print("-" * 40)

    master_key = manager.generate_key(alias="master")
    large_data = b"Large sensitive data " * 100

    enc_data, enc_key = manager.envelope_encrypt(large_data, "master")
    print(f"   Data size: {len(large_data)} bytes")
    print(f"   Encrypted data: {len(enc_data.ciphertext)} bytes")
    print(f"   Encrypted key: {len(enc_key.ciphertext)} bytes")

    decrypted = manager.envelope_decrypt(enc_data, enc_key, "master")
    print(f"   Decrypted matches: {decrypted == large_data}")
    print()

    # 9. Key Rotation
    print("9. KEY ROTATION:")
    print("-" * 40)

    old_key = manager.key_manager.get_key("main")
    new_key = manager.key_manager.rotate_key(old_key.id)

    print(f"   Old key: {old_key.id[:16]}...")
    print(f"   New key: {new_key.id[:16]}...")
    print(f"   Rotated from: {new_key.rotated_from[:16]}...")
    print()

    # 10. Statistics
    print("10. STATISTICS:")
    print("-" * 40)

    stats = manager.get_statistics()
    for key, value in stats.items():
        print(f"    {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Encryption Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
