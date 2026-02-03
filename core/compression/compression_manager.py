#!/usr/bin/env python3
"""
BAEL - Compression Manager
Advanced compression and decompression utilities.

Features:
- Multiple compression algorithms (gzip, deflate, lz77, rle, huffman)
- Streaming compression
- Compression level control
- File compression
- Archive management
- Compression statistics
- Auto-detection of best algorithm
- Memory-efficient processing
"""

import asyncio
import base64
import heapq
import io
import json
import logging
import struct
import uuid
import zlib
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (Any, BinaryIO, Callable, Dict, Generator, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class CompressionAlgorithm(Enum):
    """Compression algorithms."""
    NONE = "none"
    GZIP = "gzip"
    DEFLATE = "deflate"
    RLE = "rle"
    LZ77 = "lz77"
    HUFFMAN = "huffman"
    BROTLI = "brotli"


class CompressionLevel(Enum):
    """Compression levels."""
    NONE = 0
    FASTEST = 1
    FAST = 3
    DEFAULT = 6
    BEST = 9
    MAXIMUM = 9


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class CompressionResult:
    """Result of compression operation."""
    data: bytes
    original_size: int
    compressed_size: int
    algorithm: CompressionAlgorithm
    level: CompressionLevel
    compression_time_ms: float = 0.0

    @property
    def ratio(self) -> float:
        if self.original_size == 0:
            return 0.0
        return self.compressed_size / self.original_size

    @property
    def savings(self) -> float:
        return 1.0 - self.ratio


@dataclass
class DecompressionResult:
    """Result of decompression operation."""
    data: bytes
    compressed_size: int
    decompressed_size: int
    algorithm: CompressionAlgorithm
    decompression_time_ms: float = 0.0


@dataclass
class ArchiveEntry:
    """Archive file entry."""
    name: str
    data: bytes
    original_size: int
    compressed_size: int
    compression: CompressionAlgorithm = CompressionAlgorithm.DEFLATE
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CompressionStats:
    """Compression statistics."""
    total_original_bytes: int = 0
    total_compressed_bytes: int = 0
    total_operations: int = 0
    total_time_ms: float = 0.0
    by_algorithm: Dict[str, int] = field(default_factory=dict)

    @property
    def overall_ratio(self) -> float:
        if self.total_original_bytes == 0:
            return 0.0
        return self.total_compressed_bytes / self.total_original_bytes


# =============================================================================
# COMPRESSORS
# =============================================================================

class Compressor(ABC):
    """Base compressor."""

    algorithm: CompressionAlgorithm = CompressionAlgorithm.NONE

    @abstractmethod
    def compress(self, data: bytes, level: CompressionLevel = CompressionLevel.DEFAULT) -> bytes:
        pass

    @abstractmethod
    def decompress(self, data: bytes) -> bytes:
        pass


class NoCompressor(Compressor):
    """No compression (passthrough)."""

    algorithm = CompressionAlgorithm.NONE

    def compress(self, data: bytes, level: CompressionLevel = CompressionLevel.DEFAULT) -> bytes:
        return data

    def decompress(self, data: bytes) -> bytes:
        return data


class GzipCompressor(Compressor):
    """Gzip compression using zlib."""

    algorithm = CompressionAlgorithm.GZIP

    def compress(self, data: bytes, level: CompressionLevel = CompressionLevel.DEFAULT) -> bytes:
        return zlib.compress(data, level.value)

    def decompress(self, data: bytes) -> bytes:
        return zlib.decompress(data)


class DeflateCompressor(Compressor):
    """Deflate compression."""

    algorithm = CompressionAlgorithm.DEFLATE

    def compress(self, data: bytes, level: CompressionLevel = CompressionLevel.DEFAULT) -> bytes:
        compressor = zlib.compressobj(level.value, zlib.DEFLATED, -zlib.MAX_WBITS)
        result = compressor.compress(data)
        result += compressor.flush()
        return result

    def decompress(self, data: bytes) -> bytes:
        decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
        return decompressor.decompress(data)


class RLECompressor(Compressor):
    """Run-Length Encoding compression."""

    algorithm = CompressionAlgorithm.RLE

    def compress(self, data: bytes, level: CompressionLevel = CompressionLevel.DEFAULT) -> bytes:
        if not data:
            return b''

        result = bytearray()
        i = 0

        while i < len(data):
            byte = data[i]
            count = 1

            # Count consecutive bytes
            while i + count < len(data) and data[i + count] == byte and count < 255:
                count += 1

            # Encode: if count > 2, use RLE, otherwise store as-is
            if count > 2:
                result.append(0xFF)  # Escape byte
                result.append(count)
                result.append(byte)
            else:
                for _ in range(count):
                    if byte == 0xFF:
                        result.append(0xFF)
                        result.append(1)
                        result.append(0xFF)
                    else:
                        result.append(byte)

            i += count

        return bytes(result)

    def decompress(self, data: bytes) -> bytes:
        if not data:
            return b''

        result = bytearray()
        i = 0

        while i < len(data):
            if data[i] == 0xFF and i + 2 < len(data):
                count = data[i + 1]
                byte = data[i + 2]
                result.extend([byte] * count)
                i += 3
            else:
                result.append(data[i])
                i += 1

        return bytes(result)


class LZ77Compressor(Compressor):
    """LZ77 compression (simplified)."""

    algorithm = CompressionAlgorithm.LZ77

    def __init__(self, window_size: int = 4096, lookahead_size: int = 18):
        self.window_size = window_size
        self.lookahead_size = lookahead_size

    def compress(self, data: bytes, level: CompressionLevel = CompressionLevel.DEFAULT) -> bytes:
        if not data:
            return b''

        result = bytearray()
        i = 0

        while i < len(data):
            # Search for longest match in window
            window_start = max(0, i - self.window_size)
            window = data[window_start:i]
            lookahead = data[i:i + self.lookahead_size]

            best_offset = 0
            best_length = 0

            for j in range(len(window)):
                length = 0
                while (length < len(lookahead) and
                       j + length < len(window) and
                       window[j + length] == lookahead[length]):
                    length += 1

                if length > best_length:
                    best_length = length
                    best_offset = len(window) - j

            if best_length >= 3:
                # Encode as (offset, length)
                result.append(0xFF)  # Marker
                result.extend(struct.pack('>HB', best_offset, best_length))
                i += best_length
            else:
                # Encode literal
                if data[i] == 0xFF:
                    result.append(0xFF)
                    result.append(0x00)
                else:
                    result.append(data[i])
                i += 1

        return bytes(result)

    def decompress(self, data: bytes) -> bytes:
        if not data:
            return b''

        result = bytearray()
        i = 0

        while i < len(data):
            if data[i] == 0xFF and i + 1 < len(data):
                if data[i + 1] == 0x00:
                    result.append(0xFF)
                    i += 2
                else:
                    offset, length = struct.unpack('>HB', data[i + 1:i + 4])
                    start = len(result) - offset
                    for j in range(length):
                        result.append(result[start + j])
                    i += 4
            else:
                result.append(data[i])
                i += 1

        return bytes(result)


class HuffmanCompressor(Compressor):
    """Huffman coding compression."""

    algorithm = CompressionAlgorithm.HUFFMAN

    @dataclass
    class HuffmanNode:
        freq: int
        byte: Optional[int] = None
        left: Optional['HuffmanCompressor.HuffmanNode'] = None
        right: Optional['HuffmanCompressor.HuffmanNode'] = None

        def __lt__(self, other):
            return self.freq < other.freq

    def compress(self, data: bytes, level: CompressionLevel = CompressionLevel.DEFAULT) -> bytes:
        if not data:
            return b''

        # Build frequency table
        freq = Counter(data)

        # Build Huffman tree
        heap = [self.HuffmanNode(freq=f, byte=b) for b, f in freq.items()]
        heapq.heapify(heap)

        while len(heap) > 1:
            left = heapq.heappop(heap)
            right = heapq.heappop(heap)
            merged = self.HuffmanNode(freq=left.freq + right.freq, left=left, right=right)
            heapq.heappush(heap, merged)

        root = heap[0] if heap else None

        # Build code table
        codes: Dict[int, str] = {}
        self._build_codes(root, "", codes)

        # Encode data
        bits = ""
        for byte in data:
            bits += codes.get(byte, "")

        # Pad to byte boundary
        padding = (8 - len(bits) % 8) % 8
        bits += "0" * padding

        # Convert bits to bytes
        encoded = bytearray()
        for i in range(0, len(bits), 8):
            encoded.append(int(bits[i:i + 8], 2))

        # Serialize tree and data
        tree_data = self._serialize_tree(root)

        result = bytearray()
        result.extend(struct.pack('>I', len(tree_data)))
        result.extend(tree_data)
        result.append(padding)
        result.extend(encoded)

        return bytes(result)

    def decompress(self, data: bytes) -> bytes:
        if not data:
            return b''

        # Parse header
        tree_size = struct.unpack('>I', data[:4])[0]
        tree_data = data[4:4 + tree_size]
        padding = data[4 + tree_size]
        encoded = data[5 + tree_size:]

        # Deserialize tree
        root, _ = self._deserialize_tree(tree_data, 0)

        # Convert bytes to bits
        bits = ""
        for byte in encoded:
            bits += format(byte, '08b')

        # Remove padding
        if padding > 0:
            bits = bits[:-padding]

        # Decode
        result = bytearray()
        node = root

        for bit in bits:
            if bit == '0':
                node = node.left if node else None
            else:
                node = node.right if node else None

            if node and node.byte is not None:
                result.append(node.byte)
                node = root

        return bytes(result)

    def _build_codes(self, node: Optional[HuffmanNode], code: str, codes: Dict[int, str]) -> None:
        if node is None:
            return

        if node.byte is not None:
            codes[node.byte] = code if code else "0"
            return

        self._build_codes(node.left, code + "0", codes)
        self._build_codes(node.right, code + "1", codes)

    def _serialize_tree(self, node: Optional[HuffmanNode]) -> bytes:
        if node is None:
            return b''

        result = bytearray()

        if node.byte is not None:
            result.append(1)  # Leaf marker
            result.append(node.byte)
        else:
            result.append(0)  # Internal node marker
            result.extend(self._serialize_tree(node.left))
            result.extend(self._serialize_tree(node.right))

        return bytes(result)

    def _deserialize_tree(self, data: bytes, pos: int) -> Tuple[Optional[HuffmanNode], int]:
        if pos >= len(data):
            return None, pos

        if data[pos] == 1:  # Leaf
            return self.HuffmanNode(freq=0, byte=data[pos + 1]), pos + 2
        else:  # Internal
            left, pos = self._deserialize_tree(data, pos + 1)
            right, pos = self._deserialize_tree(data, pos)
            return self.HuffmanNode(freq=0, left=left, right=right), pos


# =============================================================================
# STREAMING COMPRESSOR
# =============================================================================

class StreamingCompressor:
    """Streaming compression support."""

    def __init__(self, compressor: Compressor, chunk_size: int = 65536):
        self.compressor = compressor
        self.chunk_size = chunk_size
        self._zlib_obj: Optional[Any] = None

    def compress_stream(self, input_stream: BinaryIO, output_stream: BinaryIO) -> int:
        """Compress from input stream to output stream."""
        total_written = 0

        if isinstance(self.compressor, (GzipCompressor, DeflateCompressor)):
            compressor = zlib.compressobj(6)

            while True:
                chunk = input_stream.read(self.chunk_size)
                if not chunk:
                    break

                compressed = compressor.compress(chunk)
                output_stream.write(compressed)
                total_written += len(compressed)

            final = compressor.flush()
            output_stream.write(final)
            total_written += len(final)
        else:
            # For other algorithms, read all and compress
            data = input_stream.read()
            compressed = self.compressor.compress(data)
            output_stream.write(compressed)
            total_written = len(compressed)

        return total_written

    def decompress_stream(self, input_stream: BinaryIO, output_stream: BinaryIO) -> int:
        """Decompress from input stream to output stream."""
        total_written = 0

        if isinstance(self.compressor, (GzipCompressor, DeflateCompressor)):
            decompressor = zlib.decompressobj()

            while True:
                chunk = input_stream.read(self.chunk_size)
                if not chunk:
                    break

                decompressed = decompressor.decompress(chunk)
                output_stream.write(decompressed)
                total_written += len(decompressed)
        else:
            data = input_stream.read()
            decompressed = self.compressor.decompress(data)
            output_stream.write(decompressed)
            total_written = len(decompressed)

        return total_written


# =============================================================================
# ARCHIVE MANAGER
# =============================================================================

class ArchiveManager:
    """Manage compressed archives."""

    MAGIC = b'BAEL'
    VERSION = 1

    def __init__(self, compressor: Optional[Compressor] = None):
        self.compressor = compressor or DeflateCompressor()
        self.entries: List[ArchiveEntry] = []

    def add_file(self, name: str, data: bytes, metadata: Optional[Dict[str, Any]] = None) -> ArchiveEntry:
        """Add file to archive."""
        compressed = self.compressor.compress(data)

        entry = ArchiveEntry(
            name=name,
            data=compressed,
            original_size=len(data),
            compressed_size=len(compressed),
            compression=self.compressor.algorithm,
            metadata=metadata or {}
        )

        self.entries.append(entry)
        return entry

    def get_file(self, name: str) -> Optional[bytes]:
        """Get decompressed file by name."""
        for entry in self.entries:
            if entry.name == name:
                return self.compressor.decompress(entry.data)
        return None

    def list_files(self) -> List[str]:
        """List all files in archive."""
        return [e.name for e in self.entries]

    def remove_file(self, name: str) -> bool:
        """Remove file from archive."""
        for i, entry in enumerate(self.entries):
            if entry.name == name:
                self.entries.pop(i)
                return True
        return False

    def save(self, path: str) -> int:
        """Save archive to file."""
        data = self._serialize()

        with open(path, 'wb') as f:
            f.write(data)

        return len(data)

    def load(self, path: str) -> int:
        """Load archive from file."""
        with open(path, 'rb') as f:
            data = f.read()

        self._deserialize(data)
        return len(self.entries)

    def _serialize(self) -> bytes:
        """Serialize archive to bytes."""
        result = bytearray()

        # Header
        result.extend(self.MAGIC)
        result.append(self.VERSION)
        result.extend(struct.pack('>I', len(self.entries)))

        # Entries
        for entry in self.entries:
            name_bytes = entry.name.encode('utf-8')
            metadata_json = json.dumps(entry.metadata).encode('utf-8')

            result.extend(struct.pack('>H', len(name_bytes)))
            result.extend(name_bytes)
            result.extend(struct.pack('>I', entry.original_size))
            result.extend(struct.pack('>I', entry.compressed_size))
            result.extend(struct.pack('>H', len(metadata_json)))
            result.extend(metadata_json)
            result.extend(entry.data)

        return bytes(result)

    def _deserialize(self, data: bytes) -> None:
        """Deserialize archive from bytes."""
        pos = 0

        # Header
        magic = data[pos:pos + 4]
        if magic != self.MAGIC:
            raise ValueError("Invalid archive format")
        pos += 4

        version = data[pos]
        pos += 1

        entry_count = struct.unpack('>I', data[pos:pos + 4])[0]
        pos += 4

        # Entries
        self.entries = []

        for _ in range(entry_count):
            name_len = struct.unpack('>H', data[pos:pos + 2])[0]
            pos += 2

            name = data[pos:pos + name_len].decode('utf-8')
            pos += name_len

            original_size = struct.unpack('>I', data[pos:pos + 4])[0]
            pos += 4

            compressed_size = struct.unpack('>I', data[pos:pos + 4])[0]
            pos += 4

            metadata_len = struct.unpack('>H', data[pos:pos + 2])[0]
            pos += 2

            metadata = json.loads(data[pos:pos + metadata_len].decode('utf-8'))
            pos += metadata_len

            entry_data = data[pos:pos + compressed_size]
            pos += compressed_size

            entry = ArchiveEntry(
                name=name,
                data=entry_data,
                original_size=original_size,
                compressed_size=compressed_size,
                metadata=metadata
            )

            self.entries.append(entry)


# =============================================================================
# COMPRESSION MANAGER
# =============================================================================

class CompressionManager:
    """
    Compression Manager for BAEL.

    Advanced compression utilities.
    """

    def __init__(self):
        self._compressors: Dict[CompressionAlgorithm, Compressor] = {
            CompressionAlgorithm.NONE: NoCompressor(),
            CompressionAlgorithm.GZIP: GzipCompressor(),
            CompressionAlgorithm.DEFLATE: DeflateCompressor(),
            CompressionAlgorithm.RLE: RLECompressor(),
            CompressionAlgorithm.LZ77: LZ77Compressor(),
            CompressionAlgorithm.HUFFMAN: HuffmanCompressor(),
        }
        self._stats = CompressionStats()

    # -------------------------------------------------------------------------
    # COMPRESSION
    # -------------------------------------------------------------------------

    def compress(
        self,
        data: bytes,
        algorithm: CompressionAlgorithm = CompressionAlgorithm.DEFLATE,
        level: CompressionLevel = CompressionLevel.DEFAULT
    ) -> CompressionResult:
        """Compress data."""
        import time
        start = time.time()

        compressor = self._compressors.get(algorithm, self._compressors[CompressionAlgorithm.DEFLATE])
        compressed = compressor.compress(data, level)

        elapsed = (time.time() - start) * 1000

        result = CompressionResult(
            data=compressed,
            original_size=len(data),
            compressed_size=len(compressed),
            algorithm=algorithm,
            level=level,
            compression_time_ms=elapsed
        )

        # Update stats
        self._stats.total_original_bytes += len(data)
        self._stats.total_compressed_bytes += len(compressed)
        self._stats.total_operations += 1
        self._stats.total_time_ms += elapsed
        self._stats.by_algorithm[algorithm.value] = self._stats.by_algorithm.get(algorithm.value, 0) + 1

        return result

    def decompress(
        self,
        data: bytes,
        algorithm: CompressionAlgorithm = CompressionAlgorithm.DEFLATE
    ) -> DecompressionResult:
        """Decompress data."""
        import time
        start = time.time()

        compressor = self._compressors.get(algorithm, self._compressors[CompressionAlgorithm.DEFLATE])
        decompressed = compressor.decompress(data)

        elapsed = (time.time() - start) * 1000

        return DecompressionResult(
            data=decompressed,
            compressed_size=len(data),
            decompressed_size=len(decompressed),
            algorithm=algorithm,
            decompression_time_ms=elapsed
        )

    # -------------------------------------------------------------------------
    # BEST ALGORITHM
    # -------------------------------------------------------------------------

    def compress_best(
        self,
        data: bytes,
        level: CompressionLevel = CompressionLevel.DEFAULT,
        algorithms: Optional[List[CompressionAlgorithm]] = None
    ) -> CompressionResult:
        """Compress using best algorithm."""
        algorithms = algorithms or [
            CompressionAlgorithm.DEFLATE,
            CompressionAlgorithm.GZIP,
            CompressionAlgorithm.RLE,
            CompressionAlgorithm.HUFFMAN
        ]

        best_result: Optional[CompressionResult] = None

        for algo in algorithms:
            result = self.compress(data, algo, level)

            if best_result is None or result.compressed_size < best_result.compressed_size:
                best_result = result

        return best_result or self.compress(data)

    # -------------------------------------------------------------------------
    # STRING COMPRESSION
    # -------------------------------------------------------------------------

    def compress_string(
        self,
        text: str,
        algorithm: CompressionAlgorithm = CompressionAlgorithm.DEFLATE,
        encoding: str = 'utf-8'
    ) -> str:
        """Compress string to base64."""
        data = text.encode(encoding)
        result = self.compress(data, algorithm)
        return base64.b64encode(result.data).decode('ascii')

    def decompress_string(
        self,
        compressed: str,
        algorithm: CompressionAlgorithm = CompressionAlgorithm.DEFLATE,
        encoding: str = 'utf-8'
    ) -> str:
        """Decompress base64 string."""
        data = base64.b64decode(compressed.encode('ascii'))
        result = self.decompress(data, algorithm)
        return result.data.decode(encoding)

    # -------------------------------------------------------------------------
    # FILE COMPRESSION
    # -------------------------------------------------------------------------

    def compress_file(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        algorithm: CompressionAlgorithm = CompressionAlgorithm.DEFLATE,
        level: CompressionLevel = CompressionLevel.DEFAULT
    ) -> CompressionResult:
        """Compress a file."""
        with open(input_path, 'rb') as f:
            data = f.read()

        result = self.compress(data, algorithm, level)

        if output_path is None:
            output_path = input_path + '.compressed'

        with open(output_path, 'wb') as f:
            f.write(result.data)

        return result

    def decompress_file(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        algorithm: CompressionAlgorithm = CompressionAlgorithm.DEFLATE
    ) -> DecompressionResult:
        """Decompress a file."""
        with open(input_path, 'rb') as f:
            data = f.read()

        result = self.decompress(data, algorithm)

        if output_path is None:
            output_path = input_path.replace('.compressed', '') + '.decompressed'

        with open(output_path, 'wb') as f:
            f.write(result.data)

        return result

    # -------------------------------------------------------------------------
    # STREAMING
    # -------------------------------------------------------------------------

    def create_streaming_compressor(
        self,
        algorithm: CompressionAlgorithm = CompressionAlgorithm.DEFLATE,
        chunk_size: int = 65536
    ) -> StreamingCompressor:
        """Create streaming compressor."""
        compressor = self._compressors.get(algorithm, self._compressors[CompressionAlgorithm.DEFLATE])
        return StreamingCompressor(compressor, chunk_size)

    # -------------------------------------------------------------------------
    # ARCHIVES
    # -------------------------------------------------------------------------

    def create_archive(
        self,
        algorithm: CompressionAlgorithm = CompressionAlgorithm.DEFLATE
    ) -> ArchiveManager:
        """Create new archive."""
        compressor = self._compressors.get(algorithm, self._compressors[CompressionAlgorithm.DEFLATE])
        return ArchiveManager(compressor)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> CompressionStats:
        """Get compression statistics."""
        return self._stats

    def reset_stats(self) -> None:
        """Reset statistics."""
        self._stats = CompressionStats()

    # -------------------------------------------------------------------------
    # ANALYSIS
    # -------------------------------------------------------------------------

    def analyze(self, data: bytes) -> Dict[str, Any]:
        """Analyze data compressibility."""
        results = {}

        for algo in [CompressionAlgorithm.DEFLATE, CompressionAlgorithm.RLE,
                     CompressionAlgorithm.HUFFMAN, CompressionAlgorithm.LZ77]:
            try:
                result = self.compress(data, algo)
                results[algo.value] = {
                    "compressed_size": result.compressed_size,
                    "ratio": result.ratio,
                    "savings": result.savings,
                    "time_ms": result.compression_time_ms
                }
            except Exception as e:
                results[algo.value] = {"error": str(e)}

        # Find best
        best = min(
            [(k, v) for k, v in results.items() if "compressed_size" in v],
            key=lambda x: x[1]["compressed_size"],
            default=(None, None)
        )

        return {
            "original_size": len(data),
            "algorithms": results,
            "best_algorithm": best[0] if best[0] else None,
            "best_ratio": best[1]["ratio"] if best[1] else None
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Compression Manager."""
    print("=" * 70)
    print("BAEL - COMPRESSION MANAGER DEMO")
    print("Advanced Compression Utilities")
    print("=" * 70)
    print()

    manager = CompressionManager()

    # Test data
    test_text = """
    BAEL - The Lord of All AI Agents

    This is a test document for compression. It contains repetitive patterns
    that should compress well. The quick brown fox jumps over the lazy dog.
    The quick brown fox jumps over the lazy dog. The quick brown fox jumps
    over the lazy dog. Numbers: 12345678901234567890123456789012345678901234567890

    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB
    """ * 3
    test_data = test_text.encode('utf-8')

    # 1. Basic Compression
    print("1. BASIC COMPRESSION:")
    print("-" * 40)

    result = manager.compress(test_data, CompressionAlgorithm.DEFLATE)
    print(f"   Original:   {result.original_size} bytes")
    print(f"   Compressed: {result.compressed_size} bytes")
    print(f"   Ratio:      {result.ratio:.2%}")
    print(f"   Savings:    {result.savings:.2%}")
    print(f"   Time:       {result.compression_time_ms:.2f}ms")
    print()

    # 2. Compare Algorithms
    print("2. COMPARE ALGORITHMS:")
    print("-" * 40)

    algorithms = [
        CompressionAlgorithm.DEFLATE,
        CompressionAlgorithm.GZIP,
        CompressionAlgorithm.RLE,
        CompressionAlgorithm.HUFFMAN,
        CompressionAlgorithm.LZ77
    ]

    for algo in algorithms:
        try:
            result = manager.compress(test_data, algo)
            print(f"   {algo.value:10s}: {result.compressed_size:6d} bytes ({result.ratio:.2%})")
        except Exception as e:
            print(f"   {algo.value:10s}: Error - {e}")
    print()

    # 3. Decompress and Verify
    print("3. DECOMPRESS AND VERIFY:")
    print("-" * 40)

    compressed = manager.compress(test_data, CompressionAlgorithm.DEFLATE)
    decompressed = manager.decompress(compressed.data, CompressionAlgorithm.DEFLATE)

    print(f"   Original size:     {len(test_data)} bytes")
    print(f"   Decompressed size: {decompressed.decompressed_size} bytes")
    print(f"   Data matches:      {decompressed.data == test_data}")
    print()

    # 4. Best Algorithm
    print("4. BEST ALGORITHM:")
    print("-" * 40)

    best = manager.compress_best(test_data)
    print(f"   Best algorithm: {best.algorithm.value}")
    print(f"   Size:          {best.compressed_size} bytes")
    print(f"   Ratio:         {best.ratio:.2%}")
    print()

    # 5. String Compression
    print("5. STRING COMPRESSION:")
    print("-" * 40)

    original_str = "Hello, BAEL! This is a test string." * 5
    compressed_str = manager.compress_string(original_str)
    decompressed_str = manager.decompress_string(compressed_str)

    print(f"   Original length:     {len(original_str)}")
    print(f"   Compressed (base64): {len(compressed_str)}")
    print(f"   Matches: {original_str == decompressed_str}")
    print()

    # 6. RLE for Repetitive Data
    print("6. RLE FOR REPETITIVE DATA:")
    print("-" * 40)

    repetitive = b'A' * 100 + b'B' * 50 + b'C' * 75
    rle_result = manager.compress(repetitive, CompressionAlgorithm.RLE)

    print(f"   Original:   {len(repetitive)} bytes")
    print(f"   RLE:        {rle_result.compressed_size} bytes")
    print(f"   Ratio:      {rle_result.ratio:.2%}")
    print()

    # 7. Huffman Coding
    print("7. HUFFMAN CODING:")
    print("-" * 40)

    huffman_result = manager.compress(test_data, CompressionAlgorithm.HUFFMAN)
    huffman_decomp = manager.decompress(huffman_result.data, CompressionAlgorithm.HUFFMAN)

    print(f"   Original:   {huffman_result.original_size} bytes")
    print(f"   Compressed: {huffman_result.compressed_size} bytes")
    print(f"   Verified:   {huffman_decomp.data == test_data}")
    print()

    # 8. Archive Creation
    print("8. ARCHIVE CREATION:")
    print("-" * 40)

    archive = manager.create_archive()
    archive.add_file("document.txt", test_data)
    archive.add_file("data.bin", b'\x00\x01\x02' * 100)
    archive.add_file("config.json", b'{"key": "value"}')

    print(f"   Files in archive: {archive.list_files()}")

    retrieved = archive.get_file("document.txt")
    print(f"   Retrieved matches: {retrieved == test_data}")
    print()

    # 9. Compression Levels
    print("9. COMPRESSION LEVELS:")
    print("-" * 40)

    levels = [
        CompressionLevel.FASTEST,
        CompressionLevel.FAST,
        CompressionLevel.DEFAULT,
        CompressionLevel.BEST
    ]

    for level in levels:
        result = manager.compress(test_data, CompressionAlgorithm.DEFLATE, level)
        print(f"   {level.name:10s}: {result.compressed_size:6d} bytes ({result.compression_time_ms:.2f}ms)")
    print()

    # 10. Analyze Data
    print("10. ANALYZE DATA:")
    print("-" * 40)

    analysis = manager.analyze(test_data)
    print(f"   Original size: {analysis['original_size']} bytes")
    print(f"   Best algorithm: {analysis['best_algorithm']}")
    print(f"   Best ratio: {analysis['best_ratio']:.2%}")
    print()

    # 11. Statistics
    print("11. STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()
    print(f"   Total operations:    {stats.total_operations}")
    print(f"   Total original:      {stats.total_original_bytes} bytes")
    print(f"   Total compressed:    {stats.total_compressed_bytes} bytes")
    print(f"   Overall ratio:       {stats.overall_ratio:.2%}")
    print(f"   Total time:          {stats.total_time_ms:.2f}ms")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Compression Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
