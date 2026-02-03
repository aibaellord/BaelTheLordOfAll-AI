#!/usr/bin/env python3
"""
BAEL - Compression Engine
Data compression and decompression for agents.

Features:
- Multiple compression algorithms
- Streaming compression
- Compression statistics
- Auto-detection
- Adaptive compression
"""

import asyncio
import base64
import gzip
import hashlib
import io
import json
import os
import time
import uuid
import zlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, BinaryIO, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class CompressionAlgorithm(Enum):
    """Compression algorithms."""
    NONE = "none"
    GZIP = "gzip"
    ZLIB = "zlib"
    DEFLATE = "deflate"
    LZ4 = "lz4"
    BROTLI = "brotli"


class CompressionLevel(Enum):
    """Compression levels."""
    NONE = 0
    FASTEST = 1
    FAST = 3
    DEFAULT = 6
    BEST = 9
    MAXIMUM = 9


class DataType(Enum):
    """Data types for optimization."""
    TEXT = "text"
    JSON = "json"
    BINARY = "binary"
    IMAGE = "image"
    MIXED = "mixed"


class CompressionStrategy(Enum):
    """Compression strategies."""
    SPEED = "speed"
    SIZE = "size"
    BALANCED = "balanced"
    ADAPTIVE = "adaptive"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class CompressionResult:
    """Compression result."""
    result_id: str = ""
    original_size: int = 0
    compressed_size: int = 0
    algorithm: CompressionAlgorithm = CompressionAlgorithm.GZIP
    level: int = 6
    duration_ms: float = 0.0
    checksum: str = ""
    data: bytes = b""

    def __post_init__(self):
        if not self.result_id:
            self.result_id = str(uuid.uuid4())[:8]

    @property
    def ratio(self) -> float:
        """Compression ratio."""
        if self.original_size == 0:
            return 0.0
        return self.compressed_size / self.original_size

    @property
    def savings(self) -> float:
        """Space savings percentage."""
        return (1.0 - self.ratio) * 100


@dataclass
class DecompressionResult:
    """Decompression result."""
    result_id: str = ""
    compressed_size: int = 0
    decompressed_size: int = 0
    algorithm: CompressionAlgorithm = CompressionAlgorithm.GZIP
    duration_ms: float = 0.0
    checksum: str = ""
    data: bytes = b""
    verified: bool = True

    def __post_init__(self):
        if not self.result_id:
            self.result_id = str(uuid.uuid4())[:8]


@dataclass
class CompressionStats:
    """Compression statistics."""
    total_compressed: int = 0
    total_decompressed: int = 0
    total_original_bytes: int = 0
    total_compressed_bytes: int = 0
    total_time_ms: float = 0.0
    operations: int = 0

    @property
    def average_ratio(self) -> float:
        """Average compression ratio."""
        if self.total_original_bytes == 0:
            return 0.0
        return self.total_compressed_bytes / self.total_original_bytes

    @property
    def bytes_saved(self) -> int:
        """Total bytes saved."""
        return self.total_original_bytes - self.total_compressed_bytes


@dataclass
class CompressionConfig:
    """Compression configuration."""
    default_algorithm: CompressionAlgorithm = CompressionAlgorithm.GZIP
    default_level: int = 6
    strategy: CompressionStrategy = CompressionStrategy.BALANCED
    verify_checksum: bool = True
    min_size_to_compress: int = 100


# =============================================================================
# COMPRESSOR INTERFACE
# =============================================================================

class Compressor(ABC):
    """Base compressor interface."""

    @abstractmethod
    def compress(self, data: bytes, level: int = 6) -> bytes:
        """Compress data."""
        pass

    @abstractmethod
    def decompress(self, data: bytes) -> bytes:
        """Decompress data."""
        pass

    @property
    @abstractmethod
    def algorithm(self) -> CompressionAlgorithm:
        """Get algorithm."""
        pass


# =============================================================================
# GZIP COMPRESSOR
# =============================================================================

class GzipCompressor(Compressor):
    """GZIP compression."""

    def compress(self, data: bytes, level: int = 6) -> bytes:
        """Compress with gzip."""
        return gzip.compress(data, compresslevel=level)

    def decompress(self, data: bytes) -> bytes:
        """Decompress gzip."""
        return gzip.decompress(data)

    @property
    def algorithm(self) -> CompressionAlgorithm:
        return CompressionAlgorithm.GZIP


# =============================================================================
# ZLIB COMPRESSOR
# =============================================================================

class ZlibCompressor(Compressor):
    """ZLIB compression."""

    def compress(self, data: bytes, level: int = 6) -> bytes:
        """Compress with zlib."""
        return zlib.compress(data, level=level)

    def decompress(self, data: bytes) -> bytes:
        """Decompress zlib."""
        return zlib.decompress(data)

    @property
    def algorithm(self) -> CompressionAlgorithm:
        return CompressionAlgorithm.ZLIB


# =============================================================================
# DEFLATE COMPRESSOR
# =============================================================================

class DeflateCompressor(Compressor):
    """Raw deflate compression."""

    def compress(self, data: bytes, level: int = 6) -> bytes:
        """Compress with deflate."""
        compress_obj = zlib.compressobj(level, zlib.DEFLATED, -zlib.MAX_WBITS)
        compressed = compress_obj.compress(data)
        compressed += compress_obj.flush()
        return compressed

    def decompress(self, data: bytes) -> bytes:
        """Decompress deflate."""
        decompress_obj = zlib.decompressobj(-zlib.MAX_WBITS)
        decompressed = decompress_obj.decompress(data)
        decompressed += decompress_obj.flush()
        return decompressed

    @property
    def algorithm(self) -> CompressionAlgorithm:
        return CompressionAlgorithm.DEFLATE


# =============================================================================
# NO COMPRESSION
# =============================================================================

class NoCompressor(Compressor):
    """No compression (passthrough)."""

    def compress(self, data: bytes, level: int = 0) -> bytes:
        """Return data unchanged."""
        return data

    def decompress(self, data: bytes) -> bytes:
        """Return data unchanged."""
        return data

    @property
    def algorithm(self) -> CompressionAlgorithm:
        return CompressionAlgorithm.NONE


# =============================================================================
# COMPRESSOR FACTORY
# =============================================================================

class CompressorFactory:
    """Factory for compressors."""

    _compressors: Dict[CompressionAlgorithm, Type[Compressor]] = {
        CompressionAlgorithm.NONE: NoCompressor,
        CompressionAlgorithm.GZIP: GzipCompressor,
        CompressionAlgorithm.ZLIB: ZlibCompressor,
        CompressionAlgorithm.DEFLATE: DeflateCompressor,
    }

    @classmethod
    def create(cls, algorithm: CompressionAlgorithm) -> Compressor:
        """Create a compressor."""
        compressor_class = cls._compressors.get(algorithm)

        if compressor_class:
            return compressor_class()

        return GzipCompressor()

    @classmethod
    def register(
        cls,
        algorithm: CompressionAlgorithm,
        compressor: Type[Compressor]
    ) -> None:
        """Register a compressor."""
        cls._compressors[algorithm] = compressor

    @classmethod
    def available(cls) -> List[CompressionAlgorithm]:
        """List available algorithms."""
        return list(cls._compressors.keys())


# =============================================================================
# CHECKSUM CALCULATOR
# =============================================================================

class ChecksumCalculator:
    """Calculate checksums."""

    def crc32(self, data: bytes) -> str:
        """Calculate CRC32 checksum."""
        return hex(zlib.crc32(data) & 0xffffffff)[2:]

    def adler32(self, data: bytes) -> str:
        """Calculate Adler32 checksum."""
        return hex(zlib.adler32(data) & 0xffffffff)[2:]

    def md5(self, data: bytes) -> str:
        """Calculate MD5 checksum."""
        return hashlib.md5(data).hexdigest()

    def sha256(self, data: bytes) -> str:
        """Calculate SHA256 checksum."""
        return hashlib.sha256(data).hexdigest()


# =============================================================================
# STREAMING COMPRESSOR
# =============================================================================

class StreamingCompressor:
    """Stream-based compression."""

    def __init__(
        self,
        algorithm: CompressionAlgorithm = CompressionAlgorithm.GZIP,
        level: int = 6
    ):
        self._algorithm = algorithm
        self._level = level
        self._buffer = io.BytesIO()
        self._compressor: Optional[Any] = None

    def start(self) -> None:
        """Start compression stream."""
        self._buffer = io.BytesIO()

        if self._algorithm == CompressionAlgorithm.GZIP:
            self._compressor = gzip.GzipFile(
                fileobj=self._buffer,
                mode="wb",
                compresslevel=self._level
            )
        elif self._algorithm in (CompressionAlgorithm.ZLIB, CompressionAlgorithm.DEFLATE):
            self._compressor = zlib.compressobj(self._level)
        else:
            self._compressor = None

    def write(self, data: bytes) -> int:
        """Write data to stream."""
        if self._compressor is None:
            self._buffer.write(data)
            return len(data)

        if self._algorithm == CompressionAlgorithm.GZIP:
            self._compressor.write(data)
            return len(data)
        else:
            compressed = self._compressor.compress(data)
            self._buffer.write(compressed)
            return len(compressed)

    def finish(self) -> bytes:
        """Finish compression and get result."""
        if self._algorithm == CompressionAlgorithm.GZIP and self._compressor:
            self._compressor.close()
        elif self._compressor and hasattr(self._compressor, "flush"):
            remaining = self._compressor.flush()
            self._buffer.write(remaining)

        return self._buffer.getvalue()


# =============================================================================
# STREAMING DECOMPRESSOR
# =============================================================================

class StreamingDecompressor:
    """Stream-based decompression."""

    def __init__(self, algorithm: CompressionAlgorithm = CompressionAlgorithm.GZIP):
        self._algorithm = algorithm
        self._decompressor: Optional[Any] = None
        self._output = io.BytesIO()

    def start(self) -> None:
        """Start decompression stream."""
        self._output = io.BytesIO()

        if self._algorithm == CompressionAlgorithm.GZIP:
            self._decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
        elif self._algorithm == CompressionAlgorithm.ZLIB:
            self._decompressor = zlib.decompressobj()
        elif self._algorithm == CompressionAlgorithm.DEFLATE:
            self._decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
        else:
            self._decompressor = None

    def write(self, data: bytes) -> bytes:
        """Write compressed data, return decompressed."""
        if self._decompressor is None:
            self._output.write(data)
            return data

        decompressed = self._decompressor.decompress(data)
        self._output.write(decompressed)
        return decompressed

    def finish(self) -> bytes:
        """Finish decompression."""
        if self._decompressor and hasattr(self._decompressor, "flush"):
            remaining = self._decompressor.flush()
            self._output.write(remaining)

        return self._output.getvalue()


# =============================================================================
# DATA TYPE DETECTOR
# =============================================================================

class DataTypeDetector:
    """Detect data types."""

    def detect(self, data: bytes) -> DataType:
        """Detect data type."""
        if len(data) < 4:
            return DataType.BINARY

        try:
            text = data.decode("utf-8")

            stripped = text.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                try:
                    json.loads(stripped)
                    return DataType.JSON
                except:
                    pass

            return DataType.TEXT

        except UnicodeDecodeError:
            pass

        # Check for image signatures
        if data[:3] == b"\xff\xd8\xff":  # JPEG
            return DataType.IMAGE
        if data[:8] == b"\x89PNG\r\n\x1a\n":  # PNG
            return DataType.IMAGE
        if data[:6] in (b"GIF87a", b"GIF89a"):  # GIF
            return DataType.IMAGE

        return DataType.BINARY

    def recommend_algorithm(self, data_type: DataType) -> CompressionAlgorithm:
        """Recommend algorithm for data type."""
        recommendations = {
            DataType.TEXT: CompressionAlgorithm.GZIP,
            DataType.JSON: CompressionAlgorithm.GZIP,
            DataType.BINARY: CompressionAlgorithm.ZLIB,
            DataType.IMAGE: CompressionAlgorithm.NONE,
            DataType.MIXED: CompressionAlgorithm.GZIP,
        }

        return recommendations.get(data_type, CompressionAlgorithm.GZIP)


# =============================================================================
# COMPRESSION STATS TRACKER
# =============================================================================

class StatsTracker:
    """Track compression statistics."""

    def __init__(self):
        self._stats = CompressionStats()
        self._by_algorithm: Dict[CompressionAlgorithm, CompressionStats] = {}

    def record_compression(self, result: CompressionResult) -> None:
        """Record compression operation."""
        self._stats.total_compressed += 1
        self._stats.total_original_bytes += result.original_size
        self._stats.total_compressed_bytes += result.compressed_size
        self._stats.total_time_ms += result.duration_ms
        self._stats.operations += 1

        if result.algorithm not in self._by_algorithm:
            self._by_algorithm[result.algorithm] = CompressionStats()

        alg_stats = self._by_algorithm[result.algorithm]
        alg_stats.total_compressed += 1
        alg_stats.total_original_bytes += result.original_size
        alg_stats.total_compressed_bytes += result.compressed_size
        alg_stats.total_time_ms += result.duration_ms
        alg_stats.operations += 1

    def record_decompression(self, result: DecompressionResult) -> None:
        """Record decompression operation."""
        self._stats.total_decompressed += 1
        self._stats.total_time_ms += result.duration_ms
        self._stats.operations += 1

    def get_stats(self) -> CompressionStats:
        """Get overall stats."""
        return self._stats

    def get_algorithm_stats(
        self,
        algorithm: CompressionAlgorithm
    ) -> Optional[CompressionStats]:
        """Get stats by algorithm."""
        return self._by_algorithm.get(algorithm)

    def reset(self) -> None:
        """Reset stats."""
        self._stats = CompressionStats()
        self._by_algorithm.clear()


# =============================================================================
# COMPRESSION ENGINE
# =============================================================================

class CompressionEngine:
    """
    Compression Engine for BAEL.

    Data compression and decompression.
    """

    def __init__(self, config: Optional[CompressionConfig] = None):
        self._config = config or CompressionConfig()

        self._checksum = ChecksumCalculator()
        self._detector = DataTypeDetector()
        self._stats = StatsTracker()
        self._cache: Dict[str, bytes] = {}

    # ----- Compression -----

    def compress(
        self,
        data: Union[str, bytes],
        algorithm: Optional[CompressionAlgorithm] = None,
        level: Optional[int] = None
    ) -> CompressionResult:
        """Compress data."""
        if isinstance(data, str):
            data = data.encode("utf-8")

        original_size = len(data)

        if original_size < self._config.min_size_to_compress:
            return CompressionResult(
                original_size=original_size,
                compressed_size=original_size,
                algorithm=CompressionAlgorithm.NONE,
                level=0,
                duration_ms=0.0,
                checksum=self._checksum.crc32(data),
                data=data
            )

        alg = algorithm or self._config.default_algorithm
        lvl = level if level is not None else self._config.default_level

        if self._config.strategy == CompressionStrategy.ADAPTIVE and algorithm is None:
            data_type = self._detector.detect(data)
            alg = self._detector.recommend_algorithm(data_type)

        compressor = CompressorFactory.create(alg)

        start_time = time.time()
        compressed_data = compressor.compress(data, lvl)
        duration_ms = (time.time() - start_time) * 1000

        if len(compressed_data) >= original_size:
            result = CompressionResult(
                original_size=original_size,
                compressed_size=original_size,
                algorithm=CompressionAlgorithm.NONE,
                level=0,
                duration_ms=duration_ms,
                checksum=self._checksum.crc32(data),
                data=data
            )
        else:
            result = CompressionResult(
                original_size=original_size,
                compressed_size=len(compressed_data),
                algorithm=alg,
                level=lvl,
                duration_ms=duration_ms,
                checksum=self._checksum.crc32(data),
                data=compressed_data
            )

        self._stats.record_compression(result)

        return result

    def decompress(
        self,
        data: bytes,
        algorithm: Optional[CompressionAlgorithm] = None,
        expected_checksum: Optional[str] = None
    ) -> DecompressionResult:
        """Decompress data."""
        compressed_size = len(data)

        alg = algorithm or self._detect_algorithm(data)

        if alg == CompressionAlgorithm.NONE:
            return DecompressionResult(
                compressed_size=compressed_size,
                decompressed_size=compressed_size,
                algorithm=alg,
                duration_ms=0.0,
                checksum=self._checksum.crc32(data),
                data=data,
                verified=True
            )

        compressor = CompressorFactory.create(alg)

        start_time = time.time()
        decompressed_data = compressor.decompress(data)
        duration_ms = (time.time() - start_time) * 1000

        checksum = self._checksum.crc32(decompressed_data)

        verified = True
        if expected_checksum and self._config.verify_checksum:
            verified = checksum == expected_checksum

        result = DecompressionResult(
            compressed_size=compressed_size,
            decompressed_size=len(decompressed_data),
            algorithm=alg,
            duration_ms=duration_ms,
            checksum=checksum,
            data=decompressed_data,
            verified=verified
        )

        self._stats.record_decompression(result)

        return result

    def _detect_algorithm(self, data: bytes) -> CompressionAlgorithm:
        """Detect compression algorithm."""
        if len(data) < 2:
            return CompressionAlgorithm.NONE

        if data[0:2] == b"\x1f\x8b":
            return CompressionAlgorithm.GZIP

        if data[0:2] == b"\x78\x9c" or data[0:2] == b"\x78\x01" or data[0:2] == b"\x78\xda":
            return CompressionAlgorithm.ZLIB

        return CompressionAlgorithm.NONE

    # ----- Convenience Methods -----

    def gzip(self, data: Union[str, bytes], level: int = 6) -> bytes:
        """GZIP compress."""
        result = self.compress(data, CompressionAlgorithm.GZIP, level)
        return result.data

    def gunzip(self, data: bytes) -> bytes:
        """GZIP decompress."""
        result = self.decompress(data, CompressionAlgorithm.GZIP)
        return result.data

    def zlib_compress(self, data: Union[str, bytes], level: int = 6) -> bytes:
        """ZLIB compress."""
        result = self.compress(data, CompressionAlgorithm.ZLIB, level)
        return result.data

    def zlib_decompress(self, data: bytes) -> bytes:
        """ZLIB decompress."""
        result = self.decompress(data, CompressionAlgorithm.ZLIB)
        return result.data

    def deflate(self, data: Union[str, bytes], level: int = 6) -> bytes:
        """Deflate compress."""
        result = self.compress(data, CompressionAlgorithm.DEFLATE, level)
        return result.data

    def inflate(self, data: bytes) -> bytes:
        """Inflate decompress."""
        result = self.decompress(data, CompressionAlgorithm.DEFLATE)
        return result.data

    # ----- Streaming -----

    def create_compressor(
        self,
        algorithm: Optional[CompressionAlgorithm] = None,
        level: Optional[int] = None
    ) -> StreamingCompressor:
        """Create streaming compressor."""
        alg = algorithm or self._config.default_algorithm
        lvl = level if level is not None else self._config.default_level

        compressor = StreamingCompressor(alg, lvl)
        compressor.start()
        return compressor

    def create_decompressor(
        self,
        algorithm: Optional[CompressionAlgorithm] = None
    ) -> StreamingDecompressor:
        """Create streaming decompressor."""
        alg = algorithm or self._config.default_algorithm

        decompressor = StreamingDecompressor(alg)
        decompressor.start()
        return decompressor

    # ----- String Compression -----

    def compress_string(
        self,
        text: str,
        encoding: str = "base64"
    ) -> str:
        """Compress string to encoded string."""
        result = self.compress(text)

        if encoding == "base64":
            return base64.b64encode(result.data).decode("utf-8")
        elif encoding == "hex":
            return result.data.hex()
        else:
            return base64.b64encode(result.data).decode("utf-8")

    def decompress_string(
        self,
        text: str,
        encoding: str = "base64"
    ) -> str:
        """Decompress encoded string."""
        if encoding == "base64":
            data = base64.b64decode(text)
        elif encoding == "hex":
            data = bytes.fromhex(text)
        else:
            data = base64.b64decode(text)

        result = self.decompress(data)
        return result.data.decode("utf-8")

    # ----- JSON Compression -----

    def compress_json(
        self,
        obj: Any,
        pretty: bool = False
    ) -> CompressionResult:
        """Compress JSON object."""
        if pretty:
            json_str = json.dumps(obj, indent=2)
        else:
            json_str = json.dumps(obj, separators=(",", ":"))

        return self.compress(json_str)

    def decompress_json(
        self,
        data: bytes,
        algorithm: Optional[CompressionAlgorithm] = None
    ) -> Any:
        """Decompress to JSON object."""
        result = self.decompress(data, algorithm)
        return json.loads(result.data.decode("utf-8"))

    # ----- Checksum -----

    def crc32(self, data: bytes) -> str:
        """Calculate CRC32."""
        return self._checksum.crc32(data)

    def md5(self, data: bytes) -> str:
        """Calculate MD5."""
        return self._checksum.md5(data)

    def sha256(self, data: bytes) -> str:
        """Calculate SHA256."""
        return self._checksum.sha256(data)

    # ----- Detection -----

    def detect_type(self, data: bytes) -> DataType:
        """Detect data type."""
        return self._detector.detect(data)

    def detect_algorithm(self, data: bytes) -> CompressionAlgorithm:
        """Detect compression algorithm."""
        return self._detect_algorithm(data)

    def is_compressed(self, data: bytes) -> bool:
        """Check if data is compressed."""
        return self._detect_algorithm(data) != CompressionAlgorithm.NONE

    # ----- Stats -----

    def get_stats(self) -> CompressionStats:
        """Get compression stats."""
        return self._stats.get_stats()

    def get_algorithm_stats(
        self,
        algorithm: CompressionAlgorithm
    ) -> Optional[CompressionStats]:
        """Get stats by algorithm."""
        return self._stats.get_algorithm_stats(algorithm)

    def reset_stats(self) -> None:
        """Reset stats."""
        self._stats.reset()

    # ----- Available -----

    def available_algorithms(self) -> List[CompressionAlgorithm]:
        """List available algorithms."""
        return CompressorFactory.available()

    # ----- Summary -----

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        stats = self._stats.get_stats()

        return {
            "default_algorithm": self._config.default_algorithm.value,
            "default_level": self._config.default_level,
            "strategy": self._config.strategy.value,
            "total_operations": stats.operations,
            "total_compressed": stats.total_compressed,
            "total_decompressed": stats.total_decompressed,
            "bytes_saved": stats.bytes_saved,
            "average_ratio": round(stats.average_ratio, 4),
            "available_algorithms": [a.value for a in self.available_algorithms()]
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Compression Engine."""
    print("=" * 70)
    print("BAEL - COMPRESSION ENGINE DEMO")
    print("Data Compression & Decompression")
    print("=" * 70)
    print()

    engine = CompressionEngine()

    # 1. Basic Compression
    print("1. BASIC COMPRESSION:")
    print("-" * 40)

    text = "Hello, BAEL! " * 100
    result = engine.compress(text)

    print(f"   Original: {result.original_size} bytes")
    print(f"   Compressed: {result.compressed_size} bytes")
    print(f"   Ratio: {result.ratio:.2%}")
    print(f"   Savings: {result.savings:.2f}%")
    print(f"   Algorithm: {result.algorithm.value}")
    print(f"   Duration: {result.duration_ms:.3f}ms")
    print()

    # 2. Decompression
    print("2. DECOMPRESSION:")
    print("-" * 40)

    decompressed = engine.decompress(result.data, result.algorithm)

    print(f"   Compressed: {decompressed.compressed_size} bytes")
    print(f"   Decompressed: {decompressed.decompressed_size} bytes")
    print(f"   Duration: {decompressed.duration_ms:.3f}ms")
    print(f"   Verified: {decompressed.verified}")
    print(f"   Match: {decompressed.data.decode() == text}")
    print()

    # 3. Different Algorithms
    print("3. ALGORITHM COMPARISON:")
    print("-" * 40)

    test_data = "The quick brown fox jumps over the lazy dog. " * 50

    for alg in [CompressionAlgorithm.GZIP, CompressionAlgorithm.ZLIB, CompressionAlgorithm.DEFLATE]:
        result = engine.compress(test_data, algorithm=alg)
        print(f"   {alg.value:10}: {result.compressed_size:5} bytes ({result.savings:.1f}% savings)")
    print()

    # 4. Compression Levels
    print("4. COMPRESSION LEVELS:")
    print("-" * 40)

    for level in [1, 5, 9]:
        result = engine.compress(test_data, level=level)
        print(f"   Level {level}: {result.compressed_size:5} bytes, {result.duration_ms:.3f}ms")
    print()

    # 5. Convenience Methods
    print("5. CONVENIENCE METHODS:")
    print("-" * 40)

    compressed = engine.gzip(test_data)
    print(f"   gzip: {len(compressed)} bytes")

    decompressed = engine.gunzip(compressed)
    print(f"   gunzip: {len(decompressed)} bytes")
    print(f"   Match: {decompressed.decode() == test_data}")
    print()

    # 6. String Compression
    print("6. STRING COMPRESSION:")
    print("-" * 40)

    original = "This is a test string that will be compressed and encoded."

    compressed_b64 = engine.compress_string(original, "base64")
    print(f"   Original: {len(original)} chars")
    print(f"   Compressed (base64): {len(compressed_b64)} chars")
    print(f"   Preview: {compressed_b64[:40]}...")

    restored = engine.decompress_string(compressed_b64, "base64")
    print(f"   Restored match: {restored == original}")
    print()

    # 7. JSON Compression
    print("7. JSON COMPRESSION:")
    print("-" * 40)

    json_data = {
        "name": "BAEL",
        "version": "1.0.0",
        "features": ["compression", "encryption", "caching"] * 10,
        "config": {"debug": True, "level": 5}
    }

    result = engine.compress_json(json_data)
    print(f"   JSON size: {result.original_size} bytes")
    print(f"   Compressed: {result.compressed_size} bytes")
    print(f"   Savings: {result.savings:.1f}%")

    restored_json = engine.decompress_json(result.data, result.algorithm)
    print(f"   JSON restored: {restored_json['name']}")
    print()

    # 8. Data Type Detection
    print("8. DATA TYPE DETECTION:")
    print("-" * 40)

    samples = [
        (b"Hello, World!", "text"),
        (b'{"key": "value"}', "json"),
        (b"\x89PNG\r\n\x1a\n", "image"),
        (b"\x00\x01\x02\x03", "binary"),
    ]

    for data, label in samples:
        detected = engine.detect_type(data)
        print(f"   {label}: {detected.value}")
    print()

    # 9. Algorithm Detection
    print("9. ALGORITHM DETECTION:")
    print("-" * 40)

    gzip_data = engine.gzip(b"test")
    zlib_data = engine.zlib_compress(b"test")
    raw_data = b"uncompressed"

    print(f"   GZIP data: {engine.detect_algorithm(gzip_data).value}")
    print(f"   ZLIB data: {engine.detect_algorithm(zlib_data).value}")
    print(f"   Raw data: {engine.detect_algorithm(raw_data).value}")

    print(f"   Is compressed (gzip): {engine.is_compressed(gzip_data)}")
    print(f"   Is compressed (raw): {engine.is_compressed(raw_data)}")
    print()

    # 10. Streaming Compression
    print("10. STREAMING COMPRESSION:")
    print("-" * 40)

    compressor = engine.create_compressor()

    chunks = [b"First chunk. ", b"Second chunk. ", b"Third chunk."]

    for chunk in chunks:
        compressor.write(chunk)

    compressed = compressor.finish()
    print(f"   Total chunks: {len(chunks)}")
    print(f"   Compressed size: {len(compressed)} bytes")

    decompressor = engine.create_decompressor()
    decompressor.write(compressed)
    decompressed = decompressor.finish()
    print(f"   Decompressed: {decompressed.decode()}")
    print()

    # 11. Checksums
    print("11. CHECKSUMS:")
    print("-" * 40)

    data = b"Calculate checksums for this data"

    print(f"   CRC32: {engine.crc32(data)}")
    print(f"   MD5: {engine.md5(data)}")
    print(f"   SHA256: {engine.sha256(data)[:32]}...")
    print()

    # 12. Small Data Handling
    print("12. SMALL DATA HANDLING:")
    print("-" * 40)

    small_data = "tiny"
    result = engine.compress(small_data)

    print(f"   Data: '{small_data}'")
    print(f"   Size: {result.original_size} bytes")
    print(f"   Algorithm used: {result.algorithm.value}")
    print(f"   (Skipped compression for small data)")
    print()

    # 13. Statistics
    print("13. COMPRESSION STATISTICS:")
    print("-" * 40)

    stats = engine.get_stats()
    print(f"   Total operations: {stats.operations}")
    print(f"   Compressions: {stats.total_compressed}")
    print(f"   Decompressions: {stats.total_decompressed}")
    print(f"   Total original: {stats.total_original_bytes} bytes")
    print(f"   Total compressed: {stats.total_compressed_bytes} bytes")
    print(f"   Bytes saved: {stats.bytes_saved} bytes")
    print(f"   Average ratio: {stats.average_ratio:.2%}")
    print()

    # 14. Available Algorithms
    print("14. AVAILABLE ALGORITHMS:")
    print("-" * 40)

    for alg in engine.available_algorithms():
        print(f"   - {alg.value}")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Compression Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
