"""
BAEL Encryption Engine
======================

Cryptographic operations with multiple algorithms.

"Ba'el's secrets are protected by divine encryption." — Ba'el
"""

from .encryption_engine import (
    # Enums
    EncryptionAlgorithm,
    HashAlgorithm,
    KeySize,

    # Data structures
    EncryptedData,
    KeyPair,
    EncryptionConfig,

    # Main engine
    EncryptionEngine,

    # Convenience
    encrypt,
    decrypt,
    hash_data,
    encryption_engine
)

__all__ = [
    'EncryptionAlgorithm',
    'HashAlgorithm',
    'KeySize',
    'EncryptedData',
    'KeyPair',
    'EncryptionConfig',
    'EncryptionEngine',
    'encrypt',
    'decrypt',
    'hash_data',
    'encryption_engine'
]
