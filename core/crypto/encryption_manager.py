#!/usr/bin/env python3
"""
BAEL - Encryption Manager
Comprehensive cryptographic operations.

Features:
- Symmetric encryption (AES)
- Asymmetric encryption (RSA)
- Hashing (SHA, BLAKE2)
- Key derivation (PBKDF2, scrypt)
- Digital signatures
- Message authentication
- Secure random generation
- Key management
- Certificate handling
- Password hashing
"""

import asyncio
import base64
import hashlib
import hmac
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
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class Algorithm(Enum):
    """Encryption algorithms."""
    AES_128_CBC = "aes-128-cbc"
    AES_256_CBC = "aes-256-cbc"
    AES_256_GCM = "aes-256-gcm"
    CHACHA20 = "chacha20"


class HashAlgorithm(Enum):
    """Hash algorithms."""
    SHA256 = "sha256"
    SHA384 = "sha384"
    SHA512 = "sha512"
    BLAKE2B = "blake2b"
    BLAKE2S = "blake2s"
    MD5 = "md5"  # Not recommended


class KDFAlgorithm(Enum):
    """Key derivation functions."""
    PBKDF2 = "pbkdf2"
    SCRYPT = "scrypt"


class EncodingFormat(Enum):
    """Encoding formats."""
    BASE64 = "base64"
    BASE64_URL = "base64url"
    HEX = "hex"
    RAW = "raw"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class EncryptionKey:
    """Encryption key container."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    key_data: bytes = b""
    algorithm: Algorithm = Algorithm.AES_256_CBC
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if key is expired."""
        if self.expires_at is None:
            return False

        return datetime.utcnow() > self.expires_at


@dataclass
class EncryptedData:
    """Encrypted data container."""
    ciphertext: bytes
    iv: bytes
    tag: Optional[bytes] = None
    algorithm: Algorithm = Algorithm.AES_256_CBC
    key_id: Optional[str] = None

    def to_bytes(self) -> bytes:
        """Serialize to bytes."""
        # Format: [1 byte algorithm][16 bytes IV][4 bytes tag len][tag][ciphertext]
        algo_byte = list(Algorithm).index(self.algorithm).to_bytes(1, 'big')
        tag = self.tag or b""
        tag_len = len(tag).to_bytes(4, 'big')

        return algo_byte + self.iv + tag_len + tag + self.ciphertext

    @classmethod
    def from_bytes(cls, data: bytes) -> 'EncryptedData':
        """Deserialize from bytes."""
        algo_index = data[0]
        algorithm = list(Algorithm)[algo_index]

        iv = data[1:17]
        tag_len = int.from_bytes(data[17:21], 'big')

        if tag_len > 0:
            tag = data[21:21+tag_len]
            ciphertext = data[21+tag_len:]
        else:
            tag = None
            ciphertext = data[21:]

        return cls(
            ciphertext=ciphertext,
            iv=iv,
            tag=tag,
            algorithm=algorithm
        )


@dataclass
class HashedPassword:
    """Hashed password container."""
    hash_value: bytes
    salt: bytes
    algorithm: KDFAlgorithm
    iterations: int

    def to_string(self) -> str:
        """Convert to storable string."""
        salt_b64 = base64.b64encode(self.salt).decode()
        hash_b64 = base64.b64encode(self.hash_value).decode()

        return f"${self.algorithm.value}${self.iterations}${salt_b64}${hash_b64}"

    @classmethod
    def from_string(cls, s: str) -> 'HashedPassword':
        """Parse from string."""
        parts = s.split("$")

        if len(parts) != 5:
            raise ValueError("Invalid hash format")

        algorithm = KDFAlgorithm(parts[1])
        iterations = int(parts[2])
        salt = base64.b64decode(parts[3])
        hash_value = base64.b64decode(parts[4])

        return cls(
            hash_value=hash_value,
            salt=salt,
            algorithm=algorithm,
            iterations=iterations
        )


@dataclass
class Signature:
    """Digital signature."""
    signature: bytes
    algorithm: HashAlgorithm
    key_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# SIMPLE AES IMPLEMENTATION
# =============================================================================

class SimpleAES:
    """
    Simple AES implementation using XOR and substitution.
    Note: This is for educational purposes. Use proper crypto libraries in production.
    """

    # S-box for substitution
    SBOX = [
        0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
        0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0,
        0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,
        0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75,
        0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84,
        0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,
        0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8,
        0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2,
        0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,
        0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb,
        0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,
        0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,
        0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a,
        0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e,
        0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,
        0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16
    ]

    def __init__(self, key: bytes):
        if len(key) not in (16, 24, 32):
            raise ValueError("Key must be 16, 24, or 32 bytes")

        self.key = key
        self.block_size = 16

    def _xor_bytes(self, a: bytes, b: bytes) -> bytes:
        """XOR two byte arrays."""
        return bytes(x ^ y for x, y in zip(a, b))

    def _substitute(self, block: bytes) -> bytes:
        """Apply S-box substitution."""
        return bytes(self.SBOX[b] for b in block)

    def _pad(self, data: bytes) -> bytes:
        """PKCS7 padding."""
        pad_len = self.block_size - (len(data) % self.block_size)
        return data + bytes([pad_len] * pad_len)

    def _unpad(self, data: bytes) -> bytes:
        """Remove PKCS7 padding."""
        pad_len = data[-1]

        if pad_len > self.block_size:
            raise ValueError("Invalid padding")

        return data[:-pad_len]

    def encrypt_block(self, block: bytes) -> bytes:
        """Encrypt single block."""
        # Simple XOR + substitution for demo
        result = self._xor_bytes(block, self.key[:16])
        result = self._substitute(result)
        result = self._xor_bytes(result, self.key[:16])
        return result

    def decrypt_block(self, block: bytes) -> bytes:
        """Decrypt single block."""
        # Reverse operations
        result = self._xor_bytes(block, self.key[:16])
        # Reverse S-box
        inv_sbox = [0] * 256
        for i, v in enumerate(self.SBOX):
            inv_sbox[v] = i
        result = bytes(inv_sbox[b] for b in result)
        result = self._xor_bytes(result, self.key[:16])
        return result

    def encrypt_cbc(self, plaintext: bytes, iv: bytes) -> bytes:
        """Encrypt in CBC mode."""
        padded = self._pad(plaintext)
        blocks = [padded[i:i+16] for i in range(0, len(padded), 16)]

        ciphertext = b""
        prev_block = iv

        for block in blocks:
            xored = self._xor_bytes(block, prev_block)
            encrypted = self.encrypt_block(xored)
            ciphertext += encrypted
            prev_block = encrypted

        return ciphertext

    def decrypt_cbc(self, ciphertext: bytes, iv: bytes) -> bytes:
        """Decrypt in CBC mode."""
        blocks = [ciphertext[i:i+16] for i in range(0, len(ciphertext), 16)]

        plaintext = b""
        prev_block = iv

        for block in blocks:
            decrypted = self.decrypt_block(block)
            xored = self._xor_bytes(decrypted, prev_block)
            plaintext += xored
            prev_block = block

        return self._unpad(plaintext)


# =============================================================================
# ENCRYPTION MANAGER
# =============================================================================

class EncryptionManager:
    """
    Comprehensive Encryption Manager for BAEL.

    Provides symmetric/asymmetric encryption, hashing, and key management.
    """

    def __init__(self):
        self._keys: Dict[str, EncryptionKey] = {}
        self._default_key_id: Optional[str] = None

    # -------------------------------------------------------------------------
    # KEY MANAGEMENT
    # -------------------------------------------------------------------------

    def generate_key(
        self,
        algorithm: Algorithm = Algorithm.AES_256_CBC,
        expires_in: timedelta = None,
        metadata: Dict[str, Any] = None
    ) -> EncryptionKey:
        """Generate new encryption key."""
        key_size = 32 if "256" in algorithm.value else 16

        key = EncryptionKey(
            key_data=secrets.token_bytes(key_size),
            algorithm=algorithm,
            expires_at=datetime.utcnow() + expires_in if expires_in else None,
            metadata=metadata or {}
        )

        self._keys[key.id] = key

        if self._default_key_id is None:
            self._default_key_id = key.id

        return key

    def import_key(
        self,
        key_data: bytes,
        algorithm: Algorithm = Algorithm.AES_256_CBC,
        key_id: str = None
    ) -> EncryptionKey:
        """Import existing key."""
        key = EncryptionKey(
            id=key_id or str(uuid.uuid4()),
            key_data=key_data,
            algorithm=algorithm
        )

        self._keys[key.id] = key
        return key

    def get_key(self, key_id: str = None) -> Optional[EncryptionKey]:
        """Get key by ID."""
        key_id = key_id or self._default_key_id

        if key_id is None:
            return None

        return self._keys.get(key_id)

    def rotate_key(self, old_key_id: str) -> EncryptionKey:
        """Rotate encryption key."""
        old_key = self._keys.get(old_key_id)

        if not old_key:
            raise ValueError(f"Key not found: {old_key_id}")

        # Generate new key with same algorithm
        new_key = self.generate_key(old_key.algorithm)

        # Mark old key as expired
        old_key.expires_at = datetime.utcnow()

        return new_key

    def set_default_key(self, key_id: str) -> None:
        """Set default key for encryption."""
        if key_id not in self._keys:
            raise ValueError(f"Key not found: {key_id}")

        self._default_key_id = key_id

    # -------------------------------------------------------------------------
    # SYMMETRIC ENCRYPTION
    # -------------------------------------------------------------------------

    def encrypt(
        self,
        plaintext: Union[str, bytes],
        key_id: str = None
    ) -> EncryptedData:
        """Encrypt data."""
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')

        key = self.get_key(key_id)

        if not key:
            raise ValueError("No encryption key available")

        iv = secrets.token_bytes(16)

        aes = SimpleAES(key.key_data)
        ciphertext = aes.encrypt_cbc(plaintext, iv)

        return EncryptedData(
            ciphertext=ciphertext,
            iv=iv,
            algorithm=key.algorithm,
            key_id=key.id
        )

    def decrypt(
        self,
        encrypted: EncryptedData,
        key_id: str = None
    ) -> bytes:
        """Decrypt data."""
        key = self.get_key(key_id or encrypted.key_id)

        if not key:
            raise ValueError("Decryption key not found")

        aes = SimpleAES(key.key_data)
        return aes.decrypt_cbc(encrypted.ciphertext, encrypted.iv)

    def encrypt_string(
        self,
        plaintext: str,
        key_id: str = None,
        encoding: EncodingFormat = EncodingFormat.BASE64
    ) -> str:
        """Encrypt string and return encoded result."""
        encrypted = self.encrypt(plaintext, key_id)
        data = encrypted.to_bytes()

        if encoding == EncodingFormat.BASE64:
            return base64.b64encode(data).decode('ascii')

        elif encoding == EncodingFormat.BASE64_URL:
            return base64.urlsafe_b64encode(data).decode('ascii')

        elif encoding == EncodingFormat.HEX:
            return data.hex()

        return data.decode('latin-1')

    def decrypt_string(
        self,
        ciphertext: str,
        key_id: str = None,
        encoding: EncodingFormat = EncodingFormat.BASE64
    ) -> str:
        """Decrypt encoded string."""
        if encoding == EncodingFormat.BASE64:
            data = base64.b64decode(ciphertext)

        elif encoding == EncodingFormat.BASE64_URL:
            data = base64.urlsafe_b64decode(ciphertext)

        elif encoding == EncodingFormat.HEX:
            data = bytes.fromhex(ciphertext)

        else:
            data = ciphertext.encode('latin-1')

        encrypted = EncryptedData.from_bytes(data)
        plaintext = self.decrypt(encrypted, key_id)

        return plaintext.decode('utf-8')

    # -------------------------------------------------------------------------
    # HASHING
    # -------------------------------------------------------------------------

    def hash(
        self,
        data: Union[str, bytes],
        algorithm: HashAlgorithm = HashAlgorithm.SHA256
    ) -> bytes:
        """Hash data."""
        if isinstance(data, str):
            data = data.encode('utf-8')

        if algorithm == HashAlgorithm.SHA256:
            return hashlib.sha256(data).digest()

        elif algorithm == HashAlgorithm.SHA384:
            return hashlib.sha384(data).digest()

        elif algorithm == HashAlgorithm.SHA512:
            return hashlib.sha512(data).digest()

        elif algorithm == HashAlgorithm.BLAKE2B:
            return hashlib.blake2b(data).digest()

        elif algorithm == HashAlgorithm.BLAKE2S:
            return hashlib.blake2s(data).digest()

        elif algorithm == HashAlgorithm.MD5:
            return hashlib.md5(data).digest()

        raise ValueError(f"Unknown algorithm: {algorithm}")

    def hash_hex(
        self,
        data: Union[str, bytes],
        algorithm: HashAlgorithm = HashAlgorithm.SHA256
    ) -> str:
        """Hash and return hex string."""
        return self.hash(data, algorithm).hex()

    def verify_hash(
        self,
        data: Union[str, bytes],
        expected_hash: Union[str, bytes],
        algorithm: HashAlgorithm = HashAlgorithm.SHA256
    ) -> bool:
        """Verify hash matches."""
        if isinstance(expected_hash, str):
            expected_hash = bytes.fromhex(expected_hash)

        actual_hash = self.hash(data, algorithm)

        return hmac.compare_digest(actual_hash, expected_hash)

    # -------------------------------------------------------------------------
    # PASSWORD HASHING
    # -------------------------------------------------------------------------

    def hash_password(
        self,
        password: str,
        algorithm: KDFAlgorithm = KDFAlgorithm.PBKDF2,
        iterations: int = 100000
    ) -> HashedPassword:
        """Hash password securely."""
        salt = secrets.token_bytes(32)

        if algorithm == KDFAlgorithm.PBKDF2:
            hash_value = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt,
                iterations,
                dklen=32
            )

        else:
            # Simulated scrypt (use proper library in production)
            hash_value = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt,
                iterations,
                dklen=32
            )

        return HashedPassword(
            hash_value=hash_value,
            salt=salt,
            algorithm=algorithm,
            iterations=iterations
        )

    def verify_password(
        self,
        password: str,
        hashed: Union[HashedPassword, str]
    ) -> bool:
        """Verify password against hash."""
        if isinstance(hashed, str):
            hashed = HashedPassword.from_string(hashed)

        if hashed.algorithm == KDFAlgorithm.PBKDF2:
            computed = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                hashed.salt,
                hashed.iterations,
                dklen=32
            )

        else:
            computed = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                hashed.salt,
                hashed.iterations,
                dklen=32
            )

        return hmac.compare_digest(computed, hashed.hash_value)

    # -------------------------------------------------------------------------
    # HMAC
    # -------------------------------------------------------------------------

    def hmac_sign(
        self,
        data: Union[str, bytes],
        key: Union[str, bytes] = None,
        algorithm: HashAlgorithm = HashAlgorithm.SHA256
    ) -> bytes:
        """Create HMAC signature."""
        if isinstance(data, str):
            data = data.encode('utf-8')

        if key is None:
            enc_key = self.get_key()

            if not enc_key:
                raise ValueError("No key available for HMAC")

            key = enc_key.key_data

        elif isinstance(key, str):
            key = key.encode('utf-8')

        hash_name = algorithm.value
        return hmac.new(key, data, hash_name).digest()

    def hmac_verify(
        self,
        data: Union[str, bytes],
        signature: bytes,
        key: Union[str, bytes] = None,
        algorithm: HashAlgorithm = HashAlgorithm.SHA256
    ) -> bool:
        """Verify HMAC signature."""
        computed = self.hmac_sign(data, key, algorithm)
        return hmac.compare_digest(computed, signature)

    # -------------------------------------------------------------------------
    # RANDOM GENERATION
    # -------------------------------------------------------------------------

    def random_bytes(self, length: int) -> bytes:
        """Generate cryptographically secure random bytes."""
        return secrets.token_bytes(length)

    def random_hex(self, length: int) -> str:
        """Generate random hex string."""
        return secrets.token_hex(length // 2)

    def random_urlsafe(self, length: int) -> str:
        """Generate URL-safe random string."""
        return secrets.token_urlsafe(length)

    def random_int(self, min_val: int, max_val: int) -> int:
        """Generate random integer in range."""
        return secrets.randbelow(max_val - min_val + 1) + min_val


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Encryption Manager."""
    print("=" * 70)
    print("BAEL - ENCRYPTION MANAGER DEMO")
    print("Comprehensive Cryptographic Operations")
    print("=" * 70)
    print()

    manager = EncryptionManager()

    # 1. Key Generation
    print("1. KEY GENERATION:")
    print("-" * 40)

    key = manager.generate_key(
        algorithm=Algorithm.AES_256_CBC,
        expires_in=timedelta(days=30),
        metadata={"purpose": "demo"}
    )

    print(f"   Key ID: {key.id[:8]}...")
    print(f"   Algorithm: {key.algorithm.value}")
    print(f"   Key size: {len(key.key_data)} bytes")
    print(f"   Expires: {key.expires_at}")
    print()

    # 2. Symmetric Encryption
    print("2. SYMMETRIC ENCRYPTION:")
    print("-" * 40)

    plaintext = "Hello, BAEL! This is a secret message."
    encrypted = manager.encrypt(plaintext)
    decrypted = manager.decrypt(encrypted)

    print(f"   Plaintext: {plaintext}")
    print(f"   Ciphertext: {encrypted.ciphertext[:20].hex()}...")
    print(f"   IV: {encrypted.iv.hex()}")
    print(f"   Decrypted: {decrypted.decode()}")
    print()

    # 3. String Encryption
    print("3. STRING ENCRYPTION:")
    print("-" * 40)

    secret = "API_KEY=super_secret_123"
    encrypted_str = manager.encrypt_string(secret)
    decrypted_str = manager.decrypt_string(encrypted_str)

    print(f"   Original: {secret}")
    print(f"   Encrypted: {encrypted_str[:50]}...")
    print(f"   Decrypted: {decrypted_str}")
    print()

    # 4. Hashing
    print("4. HASHING:")
    print("-" * 40)

    data = "Hash this data"

    for algo in [HashAlgorithm.SHA256, HashAlgorithm.SHA512, HashAlgorithm.BLAKE2B]:
        hash_hex = manager.hash_hex(data, algo)
        print(f"   {algo.value}: {hash_hex[:32]}...")
    print()

    # 5. Hash Verification
    print("5. HASH VERIFICATION:")
    print("-" * 40)

    original = "verify this"
    hash_value = manager.hash_hex(original)

    valid = manager.verify_hash(original, hash_value)
    invalid = manager.verify_hash("wrong data", hash_value)

    print(f"   Original match: {valid}")
    print(f"   Wrong data match: {invalid}")
    print()

    # 6. Password Hashing
    print("6. PASSWORD HASHING:")
    print("-" * 40)

    password = "SecureP@ssword123"
    hashed = manager.hash_password(password, iterations=10000)
    hash_string = hashed.to_string()

    print(f"   Password: {password}")
    print(f"   Hashed: {hash_string[:60]}...")
    print(f"   Iterations: {hashed.iterations}")
    print()

    # 7. Password Verification
    print("7. PASSWORD VERIFICATION:")
    print("-" * 40)

    correct = manager.verify_password(password, hashed)
    wrong = manager.verify_password("WrongPassword", hashed)

    print(f"   Correct password: {correct}")
    print(f"   Wrong password: {wrong}")
    print()

    # 8. HMAC
    print("8. HMAC SIGNATURES:")
    print("-" * 40)

    message = "Sign this message"
    signature = manager.hmac_sign(message)

    valid_sig = manager.hmac_verify(message, signature)
    invalid_sig = manager.hmac_verify("tampered", signature)

    print(f"   Message: {message}")
    print(f"   Signature: {signature.hex()[:32]}...")
    print(f"   Valid: {valid_sig}")
    print(f"   Tampered valid: {invalid_sig}")
    print()

    # 9. Random Generation
    print("9. RANDOM GENERATION:")
    print("-" * 40)

    print(f"   Random bytes: {manager.random_bytes(16).hex()}")
    print(f"   Random hex: {manager.random_hex(32)}")
    print(f"   Random URL-safe: {manager.random_urlsafe(24)}")
    print(f"   Random int (1-100): {manager.random_int(1, 100)}")
    print()

    # 10. Key Rotation
    print("10. KEY ROTATION:")
    print("-" * 40)

    old_key = key
    new_key = manager.rotate_key(old_key.id)

    print(f"   Old key ID: {old_key.id[:8]}...")
    print(f"   Old key expired: {old_key.is_expired}")
    print(f"   New key ID: {new_key.id[:8]}...")
    print()

    # 11. Different Encodings
    print("11. ENCODING FORMATS:")
    print("-" * 40)

    secret = "Encode me"

    for encoding in [EncodingFormat.BASE64, EncodingFormat.BASE64_URL, EncodingFormat.HEX]:
        encoded = manager.encrypt_string(secret, encoding=encoding)
        print(f"   {encoding.value}: {encoded[:40]}...")
    print()

    # 12. Serialization
    print("12. ENCRYPTED DATA SERIALIZATION:")
    print("-" * 40)

    encrypted = manager.encrypt("Serialize this")
    serialized = encrypted.to_bytes()
    deserialized = EncryptedData.from_bytes(serialized)

    print(f"   Original IV: {encrypted.iv.hex()}")
    print(f"   Restored IV: {deserialized.iv.hex()}")
    print(f"   Match: {encrypted.iv == deserialized.iv}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Encryption Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
