"""
BAEL Z-Algorithm Engine
=======================

Linear time pattern matching and string analysis.

"Ba'el computes Z-values in linear time." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger("BAEL.ZAlgorithm")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ZResult:
    """Z-algorithm result."""
    z_values: List[int]
    pattern_length: int
    matches: List[int]  # Positions where pattern starts


@dataclass
class StringStats:
    """String analysis statistics."""
    length: int
    longest_prefix_match: int
    num_distinct_substrings: int
    longest_repeated_substring: str


# ============================================================================
# Z-ALGORITHM
# ============================================================================

class ZAlgorithm:
    """
    Z-Algorithm for string matching and analysis.

    Z[i] = length of longest substring starting at i
           that matches a prefix of the string.

    Features:
    - O(n) time complexity
    - O(n) space complexity
    - Pattern matching, repeated substrings, etc.

    "Ba'el computes prefix matches." — Ba'el
    """

    def __init__(self):
        """Initialize Z-algorithm."""
        self._lock = threading.RLock()

    def compute_z(self, s: str) -> List[int]:
        """
        Compute Z-array for string.

        Z[i] = length of longest substring starting at i
               that matches a prefix of s.

        Args:
            s: Input string

        Returns:
            Z-array of same length as s
        """
        with self._lock:
            n = len(s)
            if n == 0:
                return []

            z = [0] * n
            z[0] = n  # By definition

            # [l, r] is the rightmost z-box found so far
            l, r = 0, 0

            for i in range(1, n):
                if i > r:
                    # Case 1: i is outside current z-box
                    l, r = i, i
                    while r < n and s[r - l] == s[r]:
                        r += 1
                    z[i] = r - l
                    r -= 1
                else:
                    # Case 2: i is inside current z-box
                    k = i - l  # Corresponding position in prefix

                    if z[k] < r - i + 1:
                        # Case 2a: z[k] doesn't extend past z-box
                        z[i] = z[k]
                    else:
                        # Case 2b: z[k] extends to or past z-box
                        l = i
                        while r < n and s[r - l] == s[r]:
                            r += 1
                        z[i] = r - l
                        r -= 1

            return z

    def search(self, text: str, pattern: str) -> List[int]:
        """
        Find all occurrences of pattern in text.

        Args:
            text: Text to search
            pattern: Pattern to find

        Returns:
            List of starting positions where pattern occurs
        """
        with self._lock:
            if not pattern:
                return list(range(len(text) + 1))

            if not text:
                return []

            m = len(pattern)
            n = len(text)

            # Construct combined string: pattern$text
            # Using $ as separator (any char not in pattern/text works)
            combined = pattern + "$" + text
            z = self.compute_z(combined)

            # Find positions where z[i] >= m
            matches = []
            for i in range(m + 1, len(combined)):
                if z[i] >= m:
                    matches.append(i - m - 1)

            return matches

    def search_all(
        self,
        text: str,
        pattern: str
    ) -> ZResult:
        """
        Search with full Z-array information.
        """
        m = len(pattern)
        combined = pattern + "$" + text
        z = self.compute_z(combined)

        matches = []
        for i in range(m + 1, len(combined)):
            if z[i] >= m:
                matches.append(i - m - 1)

        return ZResult(
            z_values=z,
            pattern_length=m,
            matches=matches
        )

    def longest_prefix_suffix(self, s: str) -> int:
        """
        Find longest proper prefix that is also a suffix.

        Proper means the prefix != entire string.
        """
        with self._lock:
            n = len(s)
            if n <= 1:
                return 0

            z = self.compute_z(s)

            # Check from the end
            for i in range(n - 1, 0, -1):
                if z[i] == n - i:
                    return n - i

            return 0

    def string_period(self, s: str) -> int:
        """
        Find smallest period of string.

        A period p means s[i] = s[i+p] for all valid i.
        """
        with self._lock:
            n = len(s)
            if n == 0:
                return 0

            z = self.compute_z(s)

            for i in range(1, n):
                if i + z[i] == n and n % i == 0:
                    return i

            return n  # String itself is the period

    def is_periodic(self, s: str) -> bool:
        """Check if string is periodic (period < len)."""
        return self.string_period(s) < len(s)

    def find_all_periods(self, s: str) -> List[int]:
        """Find all periods of string."""
        with self._lock:
            n = len(s)
            if n == 0:
                return []

            z = self.compute_z(s)
            periods = []

            for i in range(1, n + 1):
                # Check if i is a period
                is_period = True
                for j in range(i, n):
                    if s[j] != s[j - i]:
                        is_period = False
                        break

                if is_period:
                    periods.append(i)

            return periods


# ============================================================================
# EXTENDED Z-ALGORITHM
# ============================================================================

class ExtendedZAlgorithm:
    """
    Extended Z-algorithm with additional operations.

    "Ba'el extends the Z-box." — Ba'el
    """

    def __init__(self, s: str):
        """Initialize with string."""
        self._s = s
        self._n = len(s)
        self._z = ZAlgorithm().compute_z(s)
        self._lock = threading.RLock()

    @property
    def z_values(self) -> List[int]:
        """Get Z-array."""
        return self._z

    def prefix_match_at(self, i: int) -> int:
        """Length of prefix match starting at position i."""
        if i == 0:
            return self._n
        if i >= self._n:
            return 0
        return self._z[i]

    def longest_common_prefix(self, i: int, j: int) -> int:
        """
        LCP of suffixes starting at i and j.

        Note: This is O(n) per query. For many queries,
        use suffix array + LCP array.
        """
        with self._lock:
            if i == j:
                return self._n - i

            # Ensure i < j
            if i > j:
                i, j = j, i

            # LCP(i, j) = min(Z[j-i], n-j) if j-i < n
            if j - i < self._n:
                return min(self._z[j - i], self._n - j) if j - i > 0 else self._n - j

            return 0

    def occurrences_of_prefix(self, length: int) -> int:
        """Count occurrences of prefix of given length."""
        with self._lock:
            if length <= 0 or length > self._n:
                return 0

            count = 1  # The prefix itself
            for i in range(1, self._n):
                if self._z[i] >= length:
                    count += 1

            return count

    def distinct_prefixes(self) -> List[str]:
        """Get all distinct prefixes that appear multiple times."""
        with self._lock:
            # Find lengths of repeated prefixes
            repeated_lengths = set()
            for i in range(1, self._n):
                if self._z[i] > 0:
                    for l in range(1, self._z[i] + 1):
                        repeated_lengths.add(l)

            return [self._s[:l] for l in sorted(repeated_lengths)]


# ============================================================================
# COMPARISON WITH KMP
# ============================================================================

class ZToKMP:
    """
    Convert Z-array to KMP failure function.

    "Ba'el bridges algorithms." — Ba'el
    """

    @staticmethod
    def z_to_failure(z: List[int]) -> List[int]:
        """
        Convert Z-array to KMP failure function.

        failure[i] = length of longest proper prefix of s[0:i+1]
                     that is also a suffix.
        """
        n = len(z)
        if n == 0:
            return []

        failure = [0] * n

        for i in range(1, n):
            if z[i] > 0:
                for j in range(z[i] - 1, -1, -1):
                    if failure[i + j] > 0:
                        break
                    failure[i + j] = j + 1

        return failure

    @staticmethod
    def failure_to_z(failure: List[int]) -> List[int]:
        """Convert KMP failure function to Z-array."""
        n = len(failure)
        if n == 0:
            return []

        z = [n] + [0] * (n - 1)

        # This is more complex and requires the original string
        # to compute accurately. This is a placeholder.

        return z


# ============================================================================
# CONVENIENCE
# ============================================================================

def z_algorithm(s: str) -> List[int]:
    """Compute Z-array for string."""
    return ZAlgorithm().compute_z(s)


def z_search(text: str, pattern: str) -> List[int]:
    """Find all pattern occurrences using Z-algorithm."""
    return ZAlgorithm().search(text, pattern)


def z_first_occurrence(text: str, pattern: str) -> int:
    """Find first occurrence or -1."""
    matches = z_search(text, pattern)
    return matches[0] if matches else -1


def z_count_occurrences(text: str, pattern: str) -> int:
    """Count pattern occurrences."""
    return len(z_search(text, pattern))


def string_period(s: str) -> int:
    """Find smallest period of string."""
    return ZAlgorithm().string_period(s)


def longest_border(s: str) -> str:
    """
    Find longest proper prefix that is also suffix.

    Returns the actual substring.
    """
    length = ZAlgorithm().longest_prefix_suffix(s)
    return s[:length]


def is_rotation(s1: str, s2: str) -> bool:
    """
    Check if s2 is a rotation of s1.

    Example: "abcd" and "cdab" are rotations.
    """
    if len(s1) != len(s2):
        return False

    if len(s1) == 0:
        return True

    # s2 is rotation of s1 iff s2 appears in s1+s1
    combined = s1 + s1
    return len(z_search(combined, s2)) > 0


def count_distinct_substrings(s: str) -> int:
    """
    Count number of distinct substrings.

    Uses Z-algorithm approach.
    """
    n = len(s)
    if n == 0:
        return 0

    total = 0
    for i in range(n):
        # Consider suffix starting at i
        suffix = s[i:]
        z = z_algorithm(suffix)

        # Count new substrings
        max_prev = 0
        for j in range(1, len(suffix)):
            if z[j] > max_prev:
                max_prev = z[j]

        total += len(suffix) - max_prev

    return total
