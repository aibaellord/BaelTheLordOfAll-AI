"""
BAEL Security Engine Package
=============================

Advanced security, encryption, and protection capabilities.
"""

from .security import (
    # Enums
    EncryptionAlgorithm,
    HashAlgorithm,
    SecurityLevel,
    ThreatType,
    ScanResult,

    # Dataclasses
    EncryptedData,
    SecureToken,
    SecurityVulnerability,
    SecurityReport,

    # Classes
    SecureRandom,
    Hasher,
    SimpleEncryption,
    TokenManager,
    VulnerabilityScanner,
    RateLimiter,
    SecurityEngine,

    # Convenience instance
    security_engine
)

__all__ = [
    # Enums
    "EncryptionAlgorithm",
    "HashAlgorithm",
    "SecurityLevel",
    "ThreatType",
    "ScanResult",

    # Dataclasses
    "EncryptedData",
    "SecureToken",
    "SecurityVulnerability",
    "SecurityReport",

    # Classes
    "SecureRandom",
    "Hasher",
    "SimpleEncryption",
    "TokenManager",
    "VulnerabilityScanner",
    "RateLimiter",
    "SecurityEngine",

    # Instance
    "security_engine"
]
