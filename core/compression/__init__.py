"""
BAEL Compression Engine
=======================

Data compression with multiple algorithms.

"Ba'el compresses infinity into a single thought." — Ba'el
"""

from .compression_engine import (
    # Enums
    CompressionAlgorithm,
    CompressionLevel,

    # Data structures
    CompressionResult,
    CompressionConfig,

    # Main engine
    CompressionEngine,

    # Convenience
    compress,
    decompress,
    compression_engine
)

__all__ = [
    'CompressionAlgorithm',
    'CompressionLevel',
    'CompressionResult',
    'CompressionConfig',
    'CompressionEngine',
    'compress',
    'decompress',
    'compression_engine'
]
