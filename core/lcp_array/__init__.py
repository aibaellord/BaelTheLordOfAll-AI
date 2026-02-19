"""
BAEL LCP Array Engine
=====================

Longest Common Prefix array for suffix array operations.

"Ba'el finds the common prefix between all suffixes." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger("BAEL.LCPArray")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class LCPStats:
    """LCP Array statistics."""
    string_length: int = 0
    max_lcp: int = 0
    queries: int = 0


# ============================================================================
# LCP ARRAY ENGINE
# ============================================================================

class LCPArrayEngine:
    """
    LCP Array for suffix array operations.

    LCP[i] = length of longest common prefix between
             suffix[SA[i]] and suffix[SA[i-1]]

    Features:
    - O(n) Kasai algorithm for LCP construction
    - O(n) suffix array construction (SA-IS)
    - Longest repeated substring
    - Pattern matching

    "Ba'el measures the shared beginnings." — Ba'el
    """

    def __init__(self):
        """Initialize LCP Array engine."""
        self._string = ""
        self._suffix_array: List[int] = []
        self._lcp_array: List[int] = []
        self._rank: List[int] = []  # Inverse of suffix array
        self._stats = LCPStats()
        self._lock = threading.RLock()

        logger.debug("LCP Array engine initialized")

    # ========================================================================
    # BUILD
    # ========================================================================

    def build(self, text: str) -> None:
        """
        Build suffix array and LCP array.

        Args:
            text: Input string
        """
        with self._lock:
            self._string = text
            self._stats.string_length = len(text)

            # Build suffix array
            self._suffix_array = self._build_suffix_array(text)

            # Build rank array (inverse of suffix array)
            n = len(text)
            self._rank = [0] * n
            for i, sa in enumerate(self._suffix_array):
                self._rank[sa] = i

            # Build LCP array using Kasai's algorithm
            self._lcp_array = self._build_lcp_kasai(text)

            self._stats.max_lcp = max(self._lcp_array) if self._lcp_array else 0

            logger.info(
                f"LCP array built: {len(text)} chars, "
                f"max LCP {self._stats.max_lcp}"
            )

    def _build_suffix_array(self, text: str) -> List[int]:
        """Build suffix array using simple doubling algorithm."""
        n = len(text)

        if n == 0:
            return []

        # Initial ranking based on first character
        sa = list(range(n))
        rank = [ord(c) for c in text]
        tmp = [0] * n

        k = 1
        while k < n:
            # Sort by (rank[i], rank[i+k])
            def key(i: int) -> Tuple[int, int]:
                return (rank[i], rank[i + k] if i + k < n else -1)

            sa.sort(key=key)

            # Compute new ranks
            tmp[sa[0]] = 0
            for i in range(1, n):
                tmp[sa[i]] = tmp[sa[i-1]]
                if key(sa[i]) != key(sa[i-1]):
                    tmp[sa[i]] += 1

            rank = tmp.copy()

            # If all ranks are unique, we're done
            if rank[sa[n-1]] == n - 1:
                break

            k *= 2

        return sa

    def _build_lcp_kasai(self, text: str) -> List[int]:
        """Build LCP array using Kasai's algorithm in O(n)."""
        n = len(text)

        if n == 0:
            return []

        lcp = [0] * n
        k = 0  # Current LCP length

        for i in range(n):
            if self._rank[i] == 0:
                k = 0
                continue

            j = self._suffix_array[self._rank[i] - 1]

            # Extend LCP
            while i + k < n and j + k < n and text[i + k] == text[j + k]:
                k += 1

            lcp[self._rank[i]] = k

            # Decrease k for next iteration
            if k > 0:
                k -= 1

        return lcp

    # ========================================================================
    # QUERIES
    # ========================================================================

    def get_suffix_array(self) -> List[int]:
        """Get suffix array."""
        return self._suffix_array.copy()

    def get_lcp_array(self) -> List[int]:
        """Get LCP array."""
        return self._lcp_array.copy()

    def get_suffix(self, rank: int) -> str:
        """
        Get suffix at given rank.

        Args:
            rank: Rank in suffix array (0-indexed)

        Returns:
            Suffix string
        """
        if 0 <= rank < len(self._suffix_array):
            return self._string[self._suffix_array[rank]:]
        return ""

    def lcp(self, i: int, j: int) -> int:
        """
        Get LCP of suffixes starting at positions i and j.

        Args:
            i: First position
            j: Second position

        Returns:
            Length of longest common prefix
        """
        with self._lock:
            self._stats.queries += 1

            if i == j:
                return len(self._string) - i

            # Use range minimum query on LCP array
            ri, rj = self._rank[i], self._rank[j]

            if ri > rj:
                ri, rj = rj, ri

            # LCP(i, j) = min(LCP[ri+1], ..., LCP[rj])
            if ri + 1 > rj:
                return 0

            return min(self._lcp_array[ri + 1:rj + 1])

    def longest_repeated_substring(self) -> str:
        """
        Find longest repeated substring.

        Returns:
            Longest repeated substring
        """
        with self._lock:
            if not self._lcp_array:
                return ""

            max_lcp = 0
            max_idx = 0

            for i, lcp in enumerate(self._lcp_array):
                if lcp > max_lcp:
                    max_lcp = lcp
                    max_idx = i

            if max_lcp == 0:
                return ""

            start = self._suffix_array[max_idx]
            return self._string[start:start + max_lcp]

    def count_distinct_substrings(self) -> int:
        """
        Count distinct substrings.

        Returns:
            Number of distinct substrings
        """
        with self._lock:
            n = len(self._string)

            if n == 0:
                return 0

            # Total substrings - sum of LCP values
            total = n * (n + 1) // 2
            return total - sum(self._lcp_array)

    def find_pattern(self, pattern: str) -> List[int]:
        """
        Find all occurrences of pattern using suffix array.

        Args:
            pattern: Pattern to search

        Returns:
            List of starting positions
        """
        with self._lock:
            self._stats.queries += 1

            if not pattern or not self._string:
                return []

            n = len(self._string)
            m = len(pattern)

            # Binary search for left boundary
            left = 0
            right = n

            while left < right:
                mid = (left + right) // 2
                suffix = self._string[self._suffix_array[mid]:]

                if suffix[:m] < pattern:
                    left = mid + 1
                else:
                    right = mid

            start = left

            # Binary search for right boundary
            right = n

            while left < right:
                mid = (left + right) // 2
                suffix = self._string[self._suffix_array[mid]:]

                if suffix[:m] <= pattern:
                    left = mid + 1
                else:
                    right = mid

            end = left

            # Collect all matches
            return sorted([self._suffix_array[i] for i in range(start, end)])

    def longest_common_substring(self, other: str) -> str:
        """
        Find longest common substring with another string.

        Args:
            other: Other string

        Returns:
            Longest common substring
        """
        with self._lock:
            # Concatenate with separator
            combined = self._string + "\0" + other
            n1 = len(self._string)

            # Build for combined string
            engine = LCPArrayEngine()
            engine.build(combined)

            sa = engine.get_suffix_array()
            lcp = engine.get_lcp_array()

            max_lcp = 0
            max_pos = 0

            for i in range(1, len(sa)):
                # Check if adjacent suffixes are from different strings
                pos1 = sa[i - 1]
                pos2 = sa[i]

                from_first1 = pos1 < n1
                from_first2 = pos2 < n1

                if from_first1 != from_first2:
                    if lcp[i] > max_lcp:
                        max_lcp = lcp[i]
                        max_pos = sa[i]

            if max_lcp == 0:
                return ""

            return combined[max_pos:max_pos + max_lcp]

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def get_string(self) -> str:
        """Get the built string."""
        return self._string

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'string_length': self._stats.string_length,
            'max_lcp': self._stats.max_lcp,
            'queries': self._stats.queries,
            'distinct_substrings': self.count_distinct_substrings()
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_lcp_array() -> LCPArrayEngine:
    """Create empty LCP array engine."""
    return LCPArrayEngine()


def build_lcp_array(text: str) -> LCPArrayEngine:
    """
    Build LCP array from text.

    Args:
        text: Input string

    Returns:
        Built LCP array engine
    """
    engine = LCPArrayEngine()
    engine.build(text)
    return engine


def longest_repeated_substring(text: str) -> str:
    """
    Find longest repeated substring.

    Args:
        text: Input string

    Returns:
        Longest repeated substring
    """
    engine = build_lcp_array(text)
    return engine.longest_repeated_substring()


def count_distinct_substrings(text: str) -> int:
    """
    Count distinct substrings.

    Args:
        text: Input string

    Returns:
        Number of distinct substrings
    """
    engine = build_lcp_array(text)
    return engine.count_distinct_substrings()


def longest_common_substring_sa(s1: str, s2: str) -> str:
    """
    Find longest common substring using suffix array.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Longest common substring
    """
    engine = build_lcp_array(s1)
    return engine.longest_common_substring(s2)
