"""
BAEL Z-Function Engine
======================

Efficient pattern matching and string analysis.

"Ba'el measures prefix matches at every position." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger("BAEL.ZFunction")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ZFunctionStats:
    """Z-Function statistics."""
    string_length: int = 0
    pattern_matches: int = 0
    z_computations: int = 0


# ============================================================================
# Z-FUNCTION ENGINE
# ============================================================================

class ZFunctionEngine:
    """
    Z-Function algorithm for pattern matching.

    z[i] = length of longest string starting at position i
           that is also a prefix of the string

    Features:
    - O(n) Z-array computation
    - O(n+m) pattern matching
    - String period finding
    - Compression detection

    "Ba'el sees the prefix in every suffix." — Ba'el
    """

    def __init__(self):
        """Initialize Z-Function engine."""
        self._z_array: List[int] = []
        self._string = ""
        self._stats = ZFunctionStats()
        self._lock = threading.RLock()

        logger.debug("Z-Function engine initialized")

    # ========================================================================
    # Z-ARRAY COMPUTATION
    # ========================================================================

    def compute(self, text: str) -> List[int]:
        """
        Compute Z-array for text.

        Args:
            text: Input string

        Returns:
            Z-array where z[i] = length of longest prefix match at position i
        """
        with self._lock:
            n = len(text)
            self._string = text
            self._z_array = [0] * n
            self._stats.string_length = n

            if n == 0:
                return self._z_array

            self._z_array[0] = n  # Whole string is prefix of itself

            # Z-box [l, r) - rightmost segment matching prefix
            l, r = 0, 0

            for i in range(1, n):
                self._stats.z_computations += 1

                if i >= r:
                    # Outside Z-box, compute from scratch
                    l, r = i, i

                    while r < n and text[r - l] == text[r]:
                        r += 1

                    self._z_array[i] = r - l
                else:
                    # Inside Z-box, use previously computed value
                    k = i - l

                    if self._z_array[k] < r - i:
                        # Value fits within Z-box
                        self._z_array[i] = self._z_array[k]
                    else:
                        # Need to extend beyond Z-box
                        l = i

                        while r < n and text[r - l] == text[r]:
                            r += 1

                        self._z_array[i] = r - l

            return self._z_array

    def get_z_array(self) -> List[int]:
        """Get computed Z-array."""
        return self._z_array.copy()

    # ========================================================================
    # PATTERN MATCHING
    # ========================================================================

    def find_all(self, text: str, pattern: str) -> List[int]:
        """
        Find all occurrences of pattern in text.

        Args:
            text: Text to search in
            pattern: Pattern to find

        Returns:
            List of starting positions
        """
        with self._lock:
            if not pattern or not text:
                return []

            # Concatenate pattern$text
            combined = pattern + "$" + text
            z = self.compute(combined)

            pattern_len = len(pattern)
            matches = []

            for i in range(pattern_len + 1, len(combined)):
                if z[i] == pattern_len:
                    matches.append(i - pattern_len - 1)
                    self._stats.pattern_matches += 1

            return matches

    def find_first(self, text: str, pattern: str) -> int:
        """
        Find first occurrence of pattern.

        Args:
            text: Text to search in
            pattern: Pattern to find

        Returns:
            Starting position or -1
        """
        matches = self.find_all(text, pattern)
        return matches[0] if matches else -1

    def count_occurrences(self, text: str, pattern: str) -> int:
        """
        Count occurrences of pattern.

        Args:
            text: Text to search in
            pattern: Pattern to find

        Returns:
            Number of occurrences
        """
        return len(self.find_all(text, pattern))

    def contains(self, text: str, pattern: str) -> bool:
        """Check if text contains pattern."""
        return self.find_first(text, pattern) != -1

    # ========================================================================
    # STRING ANALYSIS
    # ========================================================================

    def find_period(self, text: str) -> int:
        """
        Find smallest period of string.

        A period p means s[i] = s[i+p] for all valid i.

        Args:
            text: Input string

        Returns:
            Smallest period
        """
        with self._lock:
            n = len(text)

            if n == 0:
                return 0

            z = self.compute(text)

            for i in range(1, n):
                # If z[i] + i == n, then i is a period
                if z[i] + i == n:
                    return i

            return n  # Whole string is the period

    def is_periodic(self, text: str) -> bool:
        """Check if string is periodic (has period < n)."""
        return self.find_period(text) < len(text)

    def count_distinct_periods(self, text: str) -> int:
        """Count number of distinct periods."""
        with self._lock:
            n = len(text)

            if n == 0:
                return 0

            z = self.compute(text)
            count = 1  # n is always a period

            for i in range(1, n):
                if z[i] + i == n:
                    count += 1

            return count

    def smallest_cover(self, text: str) -> str:
        """
        Find smallest string that covers the input.

        A string c covers s if s can be formed by overlapping copies of c.

        Args:
            text: Input string

        Returns:
            Smallest cover
        """
        period = self.find_period(text)
        return text[:period]

    def longest_prefix_suffix(self, text: str) -> int:
        """
        Find length of longest proper prefix that is also a suffix.

        Args:
            text: Input string

        Returns:
            Length of longest prefix-suffix
        """
        with self._lock:
            n = len(text)

            if n <= 1:
                return 0

            z = self.compute(text)

            # Find largest i where z[i] + i == n
            max_len = 0

            for i in range(1, n):
                if z[i] + i == n and z[i] < n:
                    max_len = max(max_len, z[i])

            return max_len

    def all_prefix_suffixes(self, text: str) -> List[int]:
        """
        Find lengths of all proper prefixes that are also suffixes.

        Args:
            text: Input string

        Returns:
            List of lengths in increasing order
        """
        with self._lock:
            n = len(text)

            if n <= 1:
                return []

            z = self.compute(text)
            lengths = []

            for i in range(1, n):
                if z[i] + i == n and z[i] < n:
                    lengths.append(z[i])

            return sorted(lengths)

    # ========================================================================
    # COMPRESSION
    # ========================================================================

    def compress(self, text: str) -> Tuple[str, int]:
        """
        Find shortest string that can generate text by repetition.

        Args:
            text: Input string

        Returns:
            (base_string, repetition_count)
        """
        period = self.find_period(text)
        base = text[:period]
        count = len(text) // period

        return (base, count)

    def decompress(self, base: str, count: int) -> str:
        """
        Generate string by repeating base.

        Args:
            base: Base string
            count: Number of repetitions

        Returns:
            Repeated string
        """
        return base * count

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'string_length': self._stats.string_length,
            'pattern_matches': self._stats.pattern_matches,
            'z_computations': self._stats.z_computations
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_z_function() -> ZFunctionEngine:
    """Create Z-Function engine."""
    return ZFunctionEngine()


def compute_z_array(text: str) -> List[int]:
    """
    Compute Z-array.

    Args:
        text: Input string

    Returns:
        Z-array
    """
    engine = ZFunctionEngine()
    return engine.compute(text)


def z_search(text: str, pattern: str) -> List[int]:
    """
    Find all pattern occurrences using Z-function.

    Args:
        text: Text to search
        pattern: Pattern to find

    Returns:
        List of starting positions
    """
    engine = ZFunctionEngine()
    return engine.find_all(text, pattern)


def find_period(text: str) -> int:
    """
    Find smallest period of string.

    Args:
        text: Input string

    Returns:
        Smallest period
    """
    engine = ZFunctionEngine()
    return engine.find_period(text)


def is_periodic(text: str) -> bool:
    """Check if string is periodic."""
    engine = ZFunctionEngine()
    return engine.is_periodic(text)


def string_compress(text: str) -> Tuple[str, int]:
    """
    Compress string to (base, count).

    Args:
        text: Input string

    Returns:
        (base_string, repetition_count)
    """
    engine = ZFunctionEngine()
    return engine.compress(text)
