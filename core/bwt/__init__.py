"""
BAEL Burrows-Wheeler Transform Engine
=====================================

Text transformation for compression and pattern matching.

"Ba'el transforms text into compressible form." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import Counter

logger = logging.getLogger("BAEL.BWT")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class BWTResult:
    """BWT transformation result."""
    bwt: str
    index: int  # Position of original string terminator


@dataclass
class BWTStats:
    """BWT statistics."""
    original_length: int = 0
    unique_chars: int = 0
    runs: int = 0  # Number of character runs (for RLE)


# ============================================================================
# BURROWS-WHEELER TRANSFORM ENGINE
# ============================================================================

class BWTEngine:
    """
    Burrows-Wheeler Transform for compression and search.

    Features:
    - O(n log n) forward transform
    - O(n) inverse transform
    - Pattern matching using FM-index
    - Run-length encoding optimization

    "Ba'el rearranges reality for compression." — Ba'el
    """

    def __init__(self):
        """Initialize BWT engine."""
        self._original = ""
        self._bwt = ""
        self._index = -1
        self._suffix_array: List[int] = []
        self._c: Dict[str, int] = {}  # Count of chars lexicographically smaller
        self._occ: Dict[str, List[int]] = {}  # Occurrence counts
        self._stats = BWTStats()
        self._lock = threading.RLock()

        logger.debug("BWT engine initialized")

    # ========================================================================
    # TRANSFORM
    # ========================================================================

    def transform(self, text: str, terminator: str = "$") -> BWTResult:
        """
        Compute BWT of text.

        Args:
            text: Input string
            terminator: End of string marker (must be lexicographically smallest)

        Returns:
            BWTResult with BWT string and index
        """
        with self._lock:
            self._original = text

            if not text:
                self._bwt = ""
                self._index = 0
                return BWTResult(bwt="", index=0)

            # Add terminator
            s = text + terminator
            n = len(s)

            self._stats.original_length = len(text)

            # Build suffix array
            self._suffix_array = self._build_suffix_array(s)

            # BWT is last column of sorted rotations
            bwt_chars = []
            index = -1

            for i, sa in enumerate(self._suffix_array):
                if sa == 0:
                    bwt_chars.append(s[-1])
                    index = i
                else:
                    bwt_chars.append(s[sa - 1])

            self._bwt = "".join(bwt_chars)
            self._index = index

            # Build FM-index structures
            self._build_fm_index()

            # Update stats
            self._stats.unique_chars = len(set(self._bwt))
            self._stats.runs = self._count_runs()

            logger.info(f"BWT computed: {len(text)} chars, {self._stats.runs} runs")

            return BWTResult(bwt=self._bwt, index=self._index)

    def _build_suffix_array(self, text: str) -> List[int]:
        """Build suffix array."""
        n = len(text)
        sa = list(range(n))
        rank = [ord(c) for c in text]
        tmp = [0] * n

        k = 1
        while k < n:
            def key(i: int) -> Tuple[int, int]:
                return (rank[i], rank[i + k] if i + k < n else -1)

            sa.sort(key=key)

            tmp[sa[0]] = 0
            for i in range(1, n):
                tmp[sa[i]] = tmp[sa[i-1]]
                if key(sa[i]) != key(sa[i-1]):
                    tmp[sa[i]] += 1

            rank = tmp.copy()

            if rank[sa[n-1]] == n - 1:
                break

            k *= 2

        return sa

    def _build_fm_index(self) -> None:
        """Build FM-index for pattern matching."""
        if not self._bwt:
            return

        n = len(self._bwt)

        # Count characters
        counts = Counter(self._bwt)

        # Build C array (cumulative counts of smaller chars)
        sorted_chars = sorted(counts.keys())
        cumulative = 0
        self._c = {}

        for c in sorted_chars:
            self._c[c] = cumulative
            cumulative += counts[c]

        # Build occurrence counts
        self._occ = {c: [0] for c in sorted_chars}

        for i, c in enumerate(self._bwt):
            for char in sorted_chars:
                if char == c:
                    self._occ[char].append(self._occ[char][-1] + 1)
                else:
                    self._occ[char].append(self._occ[char][-1])

    def _count_runs(self) -> int:
        """Count character runs in BWT."""
        if not self._bwt:
            return 0

        runs = 1
        for i in range(1, len(self._bwt)):
            if self._bwt[i] != self._bwt[i-1]:
                runs += 1

        return runs

    # ========================================================================
    # INVERSE TRANSFORM
    # ========================================================================

    def inverse(self, bwt: str = None, index: int = None) -> str:
        """
        Compute inverse BWT.

        Args:
            bwt: BWT string (uses stored if None)
            index: Position of terminator (uses stored if None)

        Returns:
            Original string
        """
        with self._lock:
            if bwt is None:
                bwt = self._bwt
            if index is None:
                index = self._index

            if not bwt:
                return ""

            n = len(bwt)

            # Build first column (sorted BWT)
            first = sorted(enumerate(bwt), key=lambda x: x[1])

            # Build T array (mapping from first to last column)
            t = [0] * n
            for i, (orig_idx, _) in enumerate(first):
                t[i] = orig_idx

            # Reconstruct original string
            result = []
            idx = index

            for _ in range(n - 1):  # Exclude terminator
                idx = t[idx]
                result.append(bwt[idx])

            return "".join(reversed(result))

    # ========================================================================
    # PATTERN MATCHING
    # ========================================================================

    def count(self, pattern: str) -> int:
        """
        Count occurrences of pattern using FM-index.

        Args:
            pattern: Pattern to search

        Returns:
            Number of occurrences
        """
        with self._lock:
            if not pattern or not self._bwt:
                return 0

            n = len(self._bwt)
            top = 0
            bottom = n - 1

            # Backward search
            for c in reversed(pattern):
                if c not in self._c:
                    return 0

                top = self._c[c] + self._occ[c][top]
                bottom = self._c[c] + self._occ[c][bottom + 1] - 1

                if top > bottom:
                    return 0

            return bottom - top + 1

    def find(self, pattern: str) -> List[int]:
        """
        Find all occurrences of pattern.

        Args:
            pattern: Pattern to search

        Returns:
            List of starting positions
        """
        with self._lock:
            if not pattern or not self._bwt:
                return []

            n = len(self._bwt)
            top = 0
            bottom = n - 1

            # Backward search
            for c in reversed(pattern):
                if c not in self._c:
                    return []

                top = self._c[c] + self._occ[c][top]
                bottom = self._c[c] + self._occ[c][bottom + 1] - 1

                if top > bottom:
                    return []

            # Get positions from suffix array
            positions = []
            for i in range(top, bottom + 1):
                positions.append(self._suffix_array[i])

            return sorted(positions)

    # ========================================================================
    # COMPRESSION
    # ========================================================================

    def run_length_encode(self, bwt: str = None) -> List[Tuple[str, int]]:
        """
        Run-length encode the BWT.

        Args:
            bwt: BWT string (uses stored if None)

        Returns:
            List of (char, count) pairs
        """
        with self._lock:
            if bwt is None:
                bwt = self._bwt

            if not bwt:
                return []

            result = []
            current = bwt[0]
            count = 1

            for i in range(1, len(bwt)):
                if bwt[i] == current:
                    count += 1
                else:
                    result.append((current, count))
                    current = bwt[i]
                    count = 1

            result.append((current, count))
            return result

    def run_length_decode(self, rle: List[Tuple[str, int]]) -> str:
        """
        Decode run-length encoded BWT.

        Args:
            rle: Run-length encoded data

        Returns:
            Decoded string
        """
        return "".join(char * count for char, count in rle)

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def get_bwt(self) -> str:
        """Get BWT string."""
        return self._bwt

    def get_index(self) -> int:
        """Get terminator index."""
        return self._index

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'original_length': self._stats.original_length,
            'bwt_length': len(self._bwt),
            'unique_chars': self._stats.unique_chars,
            'runs': self._stats.runs,
            'compression_potential': self._stats.original_length / max(1, self._stats.runs)
        }


# ============================================================================
# MOVE-TO-FRONT TRANSFORM
# ============================================================================

class MTFEngine:
    """
    Move-to-Front Transform (often used with BWT).

    "Ba'el moves the recent to the front." — Ba'el
    """

    @staticmethod
    def encode(text: str) -> List[int]:
        """
        Encode using MTF.

        Args:
            text: Input string

        Returns:
            List of indices
        """
        if not text:
            return []

        # Initialize alphabet
        alphabet = list(range(256))
        result = []

        for c in text:
            byte = ord(c)
            idx = alphabet.index(byte)
            result.append(idx)

            # Move to front
            alphabet.pop(idx)
            alphabet.insert(0, byte)

        return result

    @staticmethod
    def decode(indices: List[int]) -> str:
        """
        Decode MTF.

        Args:
            indices: Encoded indices

        Returns:
            Decoded string
        """
        if not indices:
            return ""

        alphabet = list(range(256))
        result = []

        for idx in indices:
            byte = alphabet[idx]
            result.append(chr(byte))

            # Move to front
            alphabet.pop(idx)
            alphabet.insert(0, byte)

        return "".join(result)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_bwt() -> BWTEngine:
    """Create empty BWT engine."""
    return BWTEngine()


def bwt_transform(text: str) -> BWTResult:
    """
    Compute BWT of text.

    Args:
        text: Input string

    Returns:
        BWTResult
    """
    engine = BWTEngine()
    return engine.transform(text)


def bwt_inverse(bwt: str, index: int) -> str:
    """
    Compute inverse BWT.

    Args:
        bwt: BWT string
        index: Terminator index

    Returns:
        Original string
    """
    engine = BWTEngine()
    return engine.inverse(bwt, index)


def bwt_count(text: str, pattern: str) -> int:
    """
    Count pattern occurrences using BWT.

    Args:
        text: Text to search in
        pattern: Pattern to find

    Returns:
        Count of occurrences
    """
    engine = BWTEngine()
    engine.transform(text)
    return engine.count(pattern)


def bwt_find(text: str, pattern: str) -> List[int]:
    """
    Find pattern positions using BWT.

    Args:
        text: Text to search in
        pattern: Pattern to find

    Returns:
        List of positions
    """
    engine = BWTEngine()
    engine.transform(text)
    return engine.find(pattern)


def mtf_encode(text: str) -> List[int]:
    """Apply Move-to-Front encoding."""
    return MTFEngine.encode(text)


def mtf_decode(indices: List[int]) -> str:
    """Apply Move-to-Front decoding."""
    return MTFEngine.decode(indices)
