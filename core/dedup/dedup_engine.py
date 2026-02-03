#!/usr/bin/env python3
"""
BAEL - Deduplication Engine
Advanced deduplication for AI agent operations.

Features:
- Content-based deduplication
- Similarity detection
- Fuzzy matching
- Bloom filters
- MinHash/LSH
- Fingerprinting
- Rolling hash
- Delta storage
- Statistics tracking
- Async operations
"""

import asyncio
import hashlib
import math
import random
import struct
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, FrozenSet, Generic,
                    Iterator, List, Optional, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class DedupStrategy(Enum):
    """Deduplication strategies."""
    EXACT = "exact"
    CONTENT_HASH = "content_hash"
    SIMILARITY = "similarity"
    FUZZY = "fuzzy"
    MINHASH = "minhash"
    SIMHASH = "simhash"


class DedupResult(Enum):
    """Deduplication result."""
    UNIQUE = "unique"
    DUPLICATE = "duplicate"
    SIMILAR = "similar"
    UNKNOWN = "unknown"


class StorageAction(Enum):
    """Storage action after dedup."""
    STORE = "store"
    SKIP = "skip"
    REFERENCE = "reference"
    DELTA = "delta"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class DedupConfig:
    """Deduplication configuration."""
    strategy: DedupStrategy = DedupStrategy.CONTENT_HASH
    similarity_threshold: float = 0.9
    num_perm: int = 128  # For MinHash
    num_bands: int = 32  # For LSH
    bloom_size: int = 10000
    bloom_hashes: int = 7
    chunk_size: int = 4096


@dataclass
class DedupEntry:
    """Deduplication entry."""
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content_hash: str = ""
    fingerprint: str = ""
    size: int = 0
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    reference_count: int = 1
    similar_to: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DedupCheckResult:
    """Result of deduplication check."""
    result: DedupResult = DedupResult.UNKNOWN
    action: StorageAction = StorageAction.STORE
    duplicate_id: Optional[str] = None
    similarity: float = 0.0
    similar_ids: List[str] = field(default_factory=list)
    content_hash: str = ""
    check_time_ms: float = 0.0


@dataclass
class DedupStats:
    """Deduplication statistics."""
    total_checked: int = 0
    unique_items: int = 0
    duplicates_found: int = 0
    similar_found: int = 0
    bytes_saved: int = 0
    dedup_ratio: float = 0.0


# =============================================================================
# BLOOM FILTER
# =============================================================================

class BloomFilter:
    """Bloom filter for fast membership testing."""

    def __init__(self, size: int = 10000, num_hashes: int = 7):
        self._size = size
        self._num_hashes = num_hashes
        self._bits = [False] * size
        self._count = 0

    def _hashes(self, item: str) -> List[int]:
        """Generate hash positions."""
        positions = []

        for i in range(self._num_hashes):
            h = hashlib.md5(f"{item}:{i}".encode()).digest()
            pos = int.from_bytes(h[:4], 'big') % self._size
            positions.append(pos)

        return positions

    def add(self, item: str) -> None:
        """Add item to filter."""
        for pos in self._hashes(item):
            self._bits[pos] = True
        self._count += 1

    def contains(self, item: str) -> bool:
        """Check if item might be in filter."""
        return all(self._bits[pos] for pos in self._hashes(item))

    def clear(self) -> None:
        """Clear the filter."""
        self._bits = [False] * self._size
        self._count = 0

    @property
    def count(self) -> int:
        """Get approximate count."""
        return self._count

    def false_positive_rate(self) -> float:
        """Estimate false positive rate."""
        bits_set = sum(self._bits)
        if self._size == 0:
            return 0.0
        return (bits_set / self._size) ** self._num_hashes


# =============================================================================
# MINHASH
# =============================================================================

class MinHash:
    """MinHash for set similarity estimation."""

    def __init__(self, num_perm: int = 128):
        self._num_perm = num_perm
        self._max_hash = 2**32 - 1
        self._a = [random.randint(1, self._max_hash) for _ in range(num_perm)]
        self._b = [random.randint(0, self._max_hash) for _ in range(num_perm)]
        self._prime = 4294967311  # Prime > max_hash

    def hash(self, item: str) -> int:
        """Hash a single item."""
        return int(hashlib.md5(item.encode()).hexdigest()[:8], 16)

    def signature(self, items: Set[str]) -> List[int]:
        """Compute MinHash signature."""
        sig = [self._max_hash] * self._num_perm

        for item in items:
            h = self.hash(item)

            for i in range(self._num_perm):
                value = (self._a[i] * h + self._b[i]) % self._prime
                sig[i] = min(sig[i], value)

        return sig

    def similarity(self, sig1: List[int], sig2: List[int]) -> float:
        """Estimate Jaccard similarity from signatures."""
        if len(sig1) != len(sig2):
            return 0.0

        matches = sum(1 for a, b in zip(sig1, sig2) if a == b)
        return matches / len(sig1)


# =============================================================================
# SIMHASH
# =============================================================================

class SimHash:
    """SimHash for near-duplicate detection."""

    def __init__(self, hash_bits: int = 64):
        self._hash_bits = hash_bits

    def _token_hash(self, token: str) -> int:
        """Hash a token to bits."""
        h = hashlib.md5(token.encode()).hexdigest()
        return int(h[:16], 16)  # 64 bits

    def hash(self, text: str) -> int:
        """Compute SimHash of text."""
        tokens = text.lower().split()

        v = [0] * self._hash_bits

        for token in tokens:
            token_hash = self._token_hash(token)

            for i in range(self._hash_bits):
                if token_hash & (1 << i):
                    v[i] += 1
                else:
                    v[i] -= 1

        fingerprint = 0
        for i in range(self._hash_bits):
            if v[i] > 0:
                fingerprint |= (1 << i)

        return fingerprint

    def distance(self, hash1: int, hash2: int) -> int:
        """Compute Hamming distance between hashes."""
        xor = hash1 ^ hash2
        return bin(xor).count('1')

    def similarity(self, hash1: int, hash2: int) -> float:
        """Compute similarity (0-1) from Hamming distance."""
        dist = self.distance(hash1, hash2)
        return 1.0 - (dist / self._hash_bits)


# =============================================================================
# LSH (Locality Sensitive Hashing)
# =============================================================================

class LSH:
    """Locality Sensitive Hashing for similarity search."""

    def __init__(self, num_perm: int = 128, num_bands: int = 32):
        self._num_perm = num_perm
        self._num_bands = num_bands
        self._rows_per_band = num_perm // num_bands
        self._buckets: List[Dict[int, Set[str]]] = [
            defaultdict(set) for _ in range(num_bands)
        ]

    def _band_hash(self, signature: List[int], band: int) -> int:
        """Hash a band of the signature."""
        start = band * self._rows_per_band
        end = start + self._rows_per_band
        band_sig = tuple(signature[start:end])
        return hash(band_sig)

    def insert(self, item_id: str, signature: List[int]) -> None:
        """Insert item into LSH."""
        for band in range(self._num_bands):
            h = self._band_hash(signature, band)
            self._buckets[band][h].add(item_id)

    def query(self, signature: List[int]) -> Set[str]:
        """Find candidate similar items."""
        candidates = set()

        for band in range(self._num_bands):
            h = self._band_hash(signature, band)
            candidates.update(self._buckets[band].get(h, set()))

        return candidates

    def remove(self, item_id: str, signature: List[int]) -> None:
        """Remove item from LSH."""
        for band in range(self._num_bands):
            h = self._band_hash(signature, band)
            self._buckets[band][h].discard(item_id)

    def clear(self) -> None:
        """Clear all buckets."""
        for bucket in self._buckets:
            bucket.clear()


# =============================================================================
# FINGERPRINTER
# =============================================================================

class Fingerprinter:
    """Content fingerprinting."""

    def __init__(self, chunk_size: int = 4096):
        self._chunk_size = chunk_size

    def md5(self, data: bytes) -> str:
        """Compute MD5 hash."""
        return hashlib.md5(data).hexdigest()

    def sha256(self, data: bytes) -> str:
        """Compute SHA-256 hash."""
        return hashlib.sha256(data).hexdigest()

    def rolling_hash(self, data: bytes, window_size: int = 64) -> List[int]:
        """Compute rolling hashes for chunking."""
        if len(data) < window_size:
            return [hash(data)]

        hashes = []
        base = 256
        mod = 2**61 - 1

        # Initial hash
        h = 0
        base_pow = pow(base, window_size - 1, mod)

        for i in range(window_size):
            h = (h * base + data[i]) % mod
        hashes.append(h)

        # Roll
        for i in range(window_size, len(data)):
            h = (h - data[i - window_size] * base_pow) % mod
            h = (h * base + data[i]) % mod
            hashes.append(h)

        return hashes

    def chunk_fingerprints(
        self,
        data: bytes,
        chunk_size: Optional[int] = None
    ) -> List[str]:
        """Compute fingerprints for fixed-size chunks."""
        size = chunk_size or self._chunk_size
        fingerprints = []

        for i in range(0, len(data), size):
            chunk = data[i:i + size]
            fingerprints.append(self.md5(chunk))

        return fingerprints

    def content_defined_chunks(
        self,
        data: bytes,
        min_size: int = 2048,
        max_size: int = 8192,
        mask: int = 0xFFF
    ) -> List[Tuple[int, int, str]]:
        """Content-defined chunking with fingerprints."""
        chunks = []
        start = 0

        hashes = self.rolling_hash(data, 48)

        for i, h in enumerate(hashes):
            size = i - start + 48

            if size >= max_size or (size >= min_size and (h & mask) == 0):
                chunk = data[start:i + 48]
                chunks.append((start, len(chunk), self.md5(chunk)))
                start = i + 48

        # Last chunk
        if start < len(data):
            chunk = data[start:]
            chunks.append((start, len(chunk), self.md5(chunk)))

        return chunks


# =============================================================================
# DEDUPLICATION ENGINE
# =============================================================================

class DeduplicationEngine:
    """
    Deduplication Engine for BAEL.

    Advanced content deduplication.
    """

    def __init__(self, config: Optional[DedupConfig] = None):
        self._config = config or DedupConfig()
        self._entries: Dict[str, DedupEntry] = {}
        self._hash_index: Dict[str, str] = {}  # hash -> entry_id
        self._bloom = BloomFilter(
            self._config.bloom_size,
            self._config.bloom_hashes
        )
        self._minhash = MinHash(self._config.num_perm)
        self._simhash = SimHash()
        self._lsh = LSH(self._config.num_perm, self._config.num_bands)
        self._fingerprinter = Fingerprinter(self._config.chunk_size)
        self._signatures: Dict[str, List[int]] = {}  # entry_id -> signature
        self._simhashes: Dict[str, int] = {}  # entry_id -> simhash
        self._stats = DedupStats()
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # EXACT DEDUPLICATION
    # -------------------------------------------------------------------------

    def check_exact(self, data: bytes) -> DedupCheckResult:
        """Check for exact duplicate using content hash."""
        start = time.time()

        content_hash = self._fingerprinter.sha256(data)

        with self._lock:
            self._stats.total_checked += 1

            # Quick bloom filter check
            if not self._bloom.contains(content_hash):
                self._bloom.add(content_hash)

                return DedupCheckResult(
                    result=DedupResult.UNIQUE,
                    action=StorageAction.STORE,
                    content_hash=content_hash,
                    check_time_ms=(time.time() - start) * 1000
                )

            # Check hash index
            if content_hash in self._hash_index:
                entry_id = self._hash_index[content_hash]
                entry = self._entries.get(entry_id)

                if entry:
                    entry.reference_count += 1
                    entry.last_seen = datetime.utcnow()

                    self._stats.duplicates_found += 1
                    self._stats.bytes_saved += len(data)

                    return DedupCheckResult(
                        result=DedupResult.DUPLICATE,
                        action=StorageAction.REFERENCE,
                        duplicate_id=entry_id,
                        similarity=1.0,
                        content_hash=content_hash,
                        check_time_ms=(time.time() - start) * 1000
                    )

            return DedupCheckResult(
                result=DedupResult.UNIQUE,
                action=StorageAction.STORE,
                content_hash=content_hash,
                check_time_ms=(time.time() - start) * 1000
            )

    # -------------------------------------------------------------------------
    # SIMILARITY DEDUPLICATION
    # -------------------------------------------------------------------------

    def check_similar(
        self,
        text: str,
        threshold: Optional[float] = None
    ) -> DedupCheckResult:
        """Check for similar content using MinHash/LSH."""
        start = time.time()
        threshold = threshold or self._config.similarity_threshold

        # Tokenize
        tokens = set(text.lower().split())
        signature = self._minhash.signature(tokens)

        with self._lock:
            self._stats.total_checked += 1

            # Find candidates via LSH
            candidates = self._lsh.query(signature)

            if not candidates:
                return DedupCheckResult(
                    result=DedupResult.UNIQUE,
                    action=StorageAction.STORE,
                    content_hash=self._fingerprinter.md5(text.encode()),
                    check_time_ms=(time.time() - start) * 1000
                )

            # Check actual similarity
            similar_ids = []
            max_similarity = 0.0
            most_similar_id = None

            for cand_id in candidates:
                if cand_id in self._signatures:
                    sim = self._minhash.similarity(
                        signature,
                        self._signatures[cand_id]
                    )

                    if sim >= threshold:
                        similar_ids.append(cand_id)

                        if sim > max_similarity:
                            max_similarity = sim
                            most_similar_id = cand_id

            if max_similarity >= 1.0 - 1e-6:
                # Exact match
                self._stats.duplicates_found += 1

                return DedupCheckResult(
                    result=DedupResult.DUPLICATE,
                    action=StorageAction.REFERENCE,
                    duplicate_id=most_similar_id,
                    similarity=max_similarity,
                    similar_ids=similar_ids,
                    content_hash=self._fingerprinter.md5(text.encode()),
                    check_time_ms=(time.time() - start) * 1000
                )

            if max_similarity >= threshold:
                # Similar
                self._stats.similar_found += 1

                return DedupCheckResult(
                    result=DedupResult.SIMILAR,
                    action=StorageAction.DELTA,
                    duplicate_id=most_similar_id,
                    similarity=max_similarity,
                    similar_ids=similar_ids,
                    content_hash=self._fingerprinter.md5(text.encode()),
                    check_time_ms=(time.time() - start) * 1000
                )

            return DedupCheckResult(
                result=DedupResult.UNIQUE,
                action=StorageAction.STORE,
                content_hash=self._fingerprinter.md5(text.encode()),
                check_time_ms=(time.time() - start) * 1000
            )

    # -------------------------------------------------------------------------
    # SIMHASH DEDUPLICATION
    # -------------------------------------------------------------------------

    def check_simhash(
        self,
        text: str,
        max_distance: int = 3
    ) -> DedupCheckResult:
        """Check for near-duplicates using SimHash."""
        start = time.time()

        sh = self._simhash.hash(text)
        content_hash = self._fingerprinter.md5(text.encode())

        with self._lock:
            self._stats.total_checked += 1

            # Find near matches
            similar_ids = []
            min_distance = float('inf')
            closest_id = None

            for entry_id, stored_sh in self._simhashes.items():
                dist = self._simhash.distance(sh, stored_sh)

                if dist <= max_distance:
                    similar_ids.append(entry_id)

                    if dist < min_distance:
                        min_distance = dist
                        closest_id = entry_id

            if min_distance == 0:
                # Exact match
                self._stats.duplicates_found += 1

                return DedupCheckResult(
                    result=DedupResult.DUPLICATE,
                    action=StorageAction.REFERENCE,
                    duplicate_id=closest_id,
                    similarity=1.0,
                    similar_ids=similar_ids,
                    content_hash=content_hash,
                    check_time_ms=(time.time() - start) * 1000
                )

            if min_distance <= max_distance:
                # Similar
                similarity = self._simhash.similarity(sh, self._simhashes[closest_id])
                self._stats.similar_found += 1

                return DedupCheckResult(
                    result=DedupResult.SIMILAR,
                    action=StorageAction.DELTA,
                    duplicate_id=closest_id,
                    similarity=similarity,
                    similar_ids=similar_ids,
                    content_hash=content_hash,
                    check_time_ms=(time.time() - start) * 1000
                )

            return DedupCheckResult(
                result=DedupResult.UNIQUE,
                action=StorageAction.STORE,
                content_hash=content_hash,
                check_time_ms=(time.time() - start) * 1000
            )

    # -------------------------------------------------------------------------
    # STORAGE OPERATIONS
    # -------------------------------------------------------------------------

    def store(
        self,
        data: bytes,
        entry_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DedupEntry:
        """Store content and return entry."""
        content_hash = self._fingerprinter.sha256(data)

        with self._lock:
            eid = entry_id or str(uuid.uuid4())

            entry = DedupEntry(
                entry_id=eid,
                content_hash=content_hash,
                fingerprint=self._fingerprinter.md5(data),
                size=len(data),
                metadata=metadata or {}
            )

            self._entries[eid] = entry
            self._hash_index[content_hash] = eid
            self._bloom.add(content_hash)

            self._stats.unique_items += 1

            return entry

    def store_text(
        self,
        text: str,
        entry_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DedupEntry:
        """Store text content with similarity indexing."""
        data = text.encode()
        entry = self.store(data, entry_id, metadata)

        # Add to similarity indexes
        tokens = set(text.lower().split())
        signature = self._minhash.signature(tokens)
        simhash = self._simhash.hash(text)

        with self._lock:
            self._signatures[entry.entry_id] = signature
            self._simhashes[entry.entry_id] = simhash
            self._lsh.insert(entry.entry_id, signature)

        return entry

    def remove(self, entry_id: str) -> bool:
        """Remove entry."""
        with self._lock:
            if entry_id not in self._entries:
                return False

            entry = self._entries.pop(entry_id)

            if entry.content_hash in self._hash_index:
                del self._hash_index[entry.content_hash]

            if entry_id in self._signatures:
                sig = self._signatures.pop(entry_id)
                self._lsh.remove(entry_id, sig)

            if entry_id in self._simhashes:
                del self._simhashes[entry_id]

            return True

    def get_entry(self, entry_id: str) -> Optional[DedupEntry]:
        """Get entry by ID."""
        with self._lock:
            return self._entries.get(entry_id)

    def find_by_hash(self, content_hash: str) -> Optional[DedupEntry]:
        """Find entry by content hash."""
        with self._lock:
            entry_id = self._hash_index.get(content_hash)
            if entry_id:
                return self._entries.get(entry_id)
            return None

    # -------------------------------------------------------------------------
    # BATCH OPERATIONS
    # -------------------------------------------------------------------------

    async def deduplicate_batch(
        self,
        items: List[bytes],
        strategy: Optional[DedupStrategy] = None
    ) -> List[DedupCheckResult]:
        """Deduplicate a batch of items."""
        strat = strategy or self._config.strategy
        results = []

        for item in items:
            if strat == DedupStrategy.EXACT or strat == DedupStrategy.CONTENT_HASH:
                result = self.check_exact(item)
            elif strat == DedupStrategy.SIMHASH:
                result = self.check_simhash(item.decode('utf-8', errors='ignore'))
            else:
                text = item.decode('utf-8', errors='ignore')
                result = self.check_similar(text)

            results.append(result)

            if result.result == DedupResult.UNIQUE:
                self.store(item)

        return results

    # -------------------------------------------------------------------------
    # CHUNK DEDUPLICATION
    # -------------------------------------------------------------------------

    def deduplicate_chunks(
        self,
        data: bytes,
        use_cdc: bool = True
    ) -> Tuple[List[str], List[Tuple[int, int, str]]]:
        """Deduplicate at chunk level."""
        if use_cdc:
            chunks = self._fingerprinter.content_defined_chunks(data)
        else:
            chunks = [(i, self._config.chunk_size, fp)
                      for i, fp in enumerate(self._fingerprinter.chunk_fingerprints(data))]

        unique_chunks = []
        chunk_refs = []

        with self._lock:
            for offset, size, fingerprint in chunks:
                if fingerprint not in self._hash_index:
                    unique_chunks.append(fingerprint)
                    self._hash_index[fingerprint] = fingerprint

                chunk_refs.append((offset, size, fingerprint))

        return unique_chunks, chunk_refs

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> DedupStats:
        """Get deduplication statistics."""
        with self._lock:
            total = self._stats.total_checked
            if total > 0:
                self._stats.dedup_ratio = (
                    self._stats.duplicates_found + self._stats.similar_found
                ) / total

            return DedupStats(
                total_checked=self._stats.total_checked,
                unique_items=self._stats.unique_items,
                duplicates_found=self._stats.duplicates_found,
                similar_found=self._stats.similar_found,
                bytes_saved=self._stats.bytes_saved,
                dedup_ratio=self._stats.dedup_ratio
            )

    def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        with self._lock:
            return {
                "entries": len(self._entries),
                "hash_index_size": len(self._hash_index),
                "signatures": len(self._signatures),
                "simhashes": len(self._simhashes),
                "bloom_fpr": self._bloom.false_positive_rate()
            }

    # -------------------------------------------------------------------------
    # MAINTENANCE
    # -------------------------------------------------------------------------

    def clear(self) -> None:
        """Clear all data."""
        with self._lock:
            self._entries.clear()
            self._hash_index.clear()
            self._signatures.clear()
            self._simhashes.clear()
            self._bloom.clear()
            self._lsh.clear()
            self._stats = DedupStats()

    def rebuild_indexes(self) -> None:
        """Rebuild similarity indexes."""
        with self._lock:
            self._lsh.clear()

            for entry_id, signature in self._signatures.items():
                self._lsh.insert(entry_id, signature)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Deduplication Engine."""
    print("=" * 70)
    print("BAEL - DEDUPLICATION ENGINE DEMO")
    print("Advanced Deduplication for AI Agents")
    print("=" * 70)
    print()

    engine = DeduplicationEngine(DedupConfig(
        similarity_threshold=0.8,
        num_perm=128,
        num_bands=32
    ))

    # 1. Exact Deduplication
    print("1. EXACT DEDUPLICATION:")
    print("-" * 40)

    data1 = b"Hello, World! This is a test document."
    data2 = b"Hello, World! This is a test document."  # Duplicate
    data3 = b"Different content here."

    result1 = engine.check_exact(data1)
    print(f"   Doc 1: {result1.result.value} (hash: {result1.content_hash[:16]}...)")
    engine.store(data1)

    result2 = engine.check_exact(data2)
    print(f"   Doc 2: {result2.result.value} (action: {result2.action.value})")

    result3 = engine.check_exact(data3)
    print(f"   Doc 3: {result3.result.value}")
    print()

    # 2. Similarity Deduplication
    print("2. SIMILARITY DEDUPLICATION:")
    print("-" * 40)

    text1 = "The quick brown fox jumps over the lazy dog"
    text2 = "The quick brown fox leaps over the lazy dog"  # Similar
    text3 = "Something completely different about cats"

    engine.store_text(text1, "text1")

    result2 = engine.check_similar(text2)
    print(f"   Text 2: {result2.result.value} (similarity: {result2.similarity:.2f})")

    result3 = engine.check_similar(text3)
    print(f"   Text 3: {result3.result.value}")
    print()

    # 3. SimHash Deduplication
    print("3. SIMHASH DEDUPLICATION:")
    print("-" * 40)

    text4 = "Machine learning is a subset of artificial intelligence"
    text5 = "Machine learning is part of artificial intelligence"  # Near-duplicate

    engine.store_text(text4, "text4")

    result5 = engine.check_simhash(text5, max_distance=10)
    print(f"   Text 5: {result5.result.value} (similarity: {result5.similarity:.2f})")
    print()

    # 4. Chunk Deduplication
    print("4. CHUNK DEDUPLICATION:")
    print("-" * 40)

    large_data = b"A" * 10000 + b"B" * 10000 + b"A" * 10000  # Repeated pattern

    unique_chunks, chunk_refs = engine.deduplicate_chunks(large_data, use_cdc=False)

    print(f"   Total chunks: {len(chunk_refs)}")
    print(f"   Unique chunks: {len(unique_chunks)}")
    print(f"   Dedup savings: {(1 - len(unique_chunks)/len(chunk_refs)):.1%}")
    print()

    # 5. MinHash Similarity
    print("5. MINHASH SIMILARITY:")
    print("-" * 40)

    minhash = engine._minhash

    set1 = {"apple", "banana", "orange", "grape"}
    set2 = {"apple", "banana", "orange", "mango"}
    set3 = {"car", "bus", "train", "plane"}

    sig1 = minhash.signature(set1)
    sig2 = minhash.signature(set2)
    sig3 = minhash.signature(set3)

    print(f"   Set1 vs Set2: {minhash.similarity(sig1, sig2):.2f}")
    print(f"   Set1 vs Set3: {minhash.similarity(sig1, sig3):.2f}")
    print()

    # 6. SimHash Similarity
    print("6. SIMHASH SIMILARITY:")
    print("-" * 40)

    simhash = engine._simhash

    sh1 = simhash.hash("Python is a great programming language")
    sh2 = simhash.hash("Python is an excellent programming language")
    sh3 = simhash.hash("JavaScript is used for web development")

    print(f"   Text1 vs Text2: {simhash.similarity(sh1, sh2):.2f} (dist: {simhash.distance(sh1, sh2)})")
    print(f"   Text1 vs Text3: {simhash.similarity(sh1, sh3):.2f} (dist: {simhash.distance(sh1, sh3)})")
    print()

    # 7. Bloom Filter
    print("7. BLOOM FILTER:")
    print("-" * 40)

    bloom = engine._bloom

    print(f"   Items: {bloom.count}")
    print(f"   False positive rate: {bloom.false_positive_rate():.4f}")
    print()

    # 8. Statistics
    print("8. STATISTICS:")
    print("-" * 40)

    stats = engine.get_stats()

    print(f"   Total checked: {stats.total_checked}")
    print(f"   Unique items: {stats.unique_items}")
    print(f"   Duplicates: {stats.duplicates_found}")
    print(f"   Similar: {stats.similar_found}")
    print(f"   Bytes saved: {stats.bytes_saved}")
    print(f"   Dedup ratio: {stats.dedup_ratio:.2%}")
    print()

    # 9. Index Statistics
    print("9. INDEX STATISTICS:")
    print("-" * 40)

    idx_stats = engine.get_index_stats()

    print(f"   Entries: {idx_stats['entries']}")
    print(f"   Hash index: {idx_stats['hash_index_size']}")
    print(f"   Signatures: {idx_stats['signatures']}")
    print(f"   SimHashes: {idx_stats['simhashes']}")
    print()

    # 10. Batch Deduplication
    print("10. BATCH DEDUPLICATION:")
    print("-" * 40)

    batch = [
        b"Unique document one",
        b"Unique document two",
        b"Unique document one",  # Duplicate
        b"Unique document three"
    ]

    results = await engine.deduplicate_batch(batch)

    for i, result in enumerate(results):
        print(f"   Item {i+1}: {result.result.value}")
    print()

    # 11. Find by Hash
    print("11. FIND BY HASH:")
    print("-" * 40)

    test_data = b"Hello, World! This is a test document."
    test_hash = engine._fingerprinter.sha256(test_data)

    entry = engine.find_by_hash(test_hash)

    if entry:
        print(f"   Found: {entry.entry_id[:8]}...")
        print(f"   Size: {entry.size} bytes")
        print(f"   References: {entry.reference_count}")
    print()

    # 12. LSH Query
    print("12. LSH QUERY:")
    print("-" * 40)

    query_text = "The quick brown fox jumps over the lazy dog"
    tokens = set(query_text.lower().split())
    query_sig = minhash.signature(tokens)

    candidates = engine._lsh.query(query_sig)

    print(f"   Query: '{query_text[:30]}...'")
    print(f"   Candidates: {len(candidates)}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Deduplication Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
