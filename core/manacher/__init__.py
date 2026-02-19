"""
BAEL Manacher's Algorithm Engine
================================

Linear time longest palindromic substring algorithm.

"Ba'el mirrors the world in linear time." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger("BAEL.Manacher")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class PalindromeInfo:
    """Information about a palindrome."""
    center: int
    length: int
    start: int
    end: int
    text: str


@dataclass
class ManacherStats:
    """Manacher's algorithm statistics."""
    string_length: int = 0
    longest_palindrome_length: int = 0
    total_palindromes: int = 0
    queries: int = 0


# ============================================================================
# MANACHER'S ALGORITHM ENGINE
# ============================================================================

class ManacherEngine:
    """
    Manacher's Algorithm for palindrome detection.

    Features:
    - O(n) longest palindromic substring
    - All palindromes in linear time
    - Odd and even length palindromes
    - Count palindromes at each center

    "Ba'el sees all reflections instantaneously." — Ba'el
    """

    def __init__(self):
        """Initialize Manacher engine."""
        self._string = ""
        self._transformed = ""
        self._p: List[int] = []  # Palindrome radii array
        self._stats = ManacherStats()
        self._lock = threading.RLock()

        logger.debug("Manacher engine initialized")

    # ========================================================================
    # BUILD
    # ========================================================================

    def build(self, text: str) -> None:
        """
        Build the palindrome array.

        Args:
            text: Input string
        """
        with self._lock:
            self._string = text
            self._stats.string_length = len(text)

            if not text:
                self._transformed = ""
                self._p = []
                return

            # Transform: "abc" -> "^#a#b#c#$"
            # This handles both odd and even palindromes uniformly
            self._transformed = "^#" + "#".join(text) + "#$"

            n = len(self._transformed)
            self._p = [0] * n

            # Manacher's algorithm
            center = 0
            right = 0

            for i in range(1, n - 1):
                if i < right:
                    # Use mirror
                    mirror = 2 * center - i
                    self._p[i] = min(right - i, self._p[mirror])

                # Expand around center
                while self._transformed[i + self._p[i] + 1] == self._transformed[i - self._p[i] - 1]:
                    self._p[i] += 1

                # Update center and right boundary
                if i + self._p[i] > right:
                    center = i
                    right = i + self._p[i]

            # Update stats
            self._stats.longest_palindrome_length = max(self._p) if self._p else 0
            self._stats.total_palindromes = sum(
                (p + 1) // 2 for p in self._p[1:-1]
            )

            logger.info(
                f"Manacher built: {len(text)} chars, "
                f"longest palindrome {self._stats.longest_palindrome_length}"
            )

    # ========================================================================
    # QUERIES
    # ========================================================================

    def longest_palindrome(self) -> str:
        """
        Get longest palindromic substring.

        Returns:
            Longest palindrome
        """
        with self._lock:
            self._stats.queries += 1

            if not self._p:
                return ""

            # Find maximum in P array
            max_len = 0
            max_center = 0

            for i in range(1, len(self._p) - 1):
                if self._p[i] > max_len:
                    max_len = self._p[i]
                    max_center = i

            # Convert back to original string indices
            start = (max_center - max_len) // 2
            return self._string[start:start + max_len]

    def longest_palindrome_info(self) -> Optional[PalindromeInfo]:
        """
        Get detailed info about longest palindrome.

        Returns:
            PalindromeInfo or None
        """
        with self._lock:
            if not self._p:
                return None

            max_len = 0
            max_center = 0

            for i in range(1, len(self._p) - 1):
                if self._p[i] > max_len:
                    max_len = self._p[i]
                    max_center = i

            start = (max_center - max_len) // 2

            return PalindromeInfo(
                center=max_center // 2 if max_center % 2 == 0 else (max_center - 1) // 2,
                length=max_len,
                start=start,
                end=start + max_len - 1,
                text=self._string[start:start + max_len]
            )

    def palindrome_at(self, center: int, odd: bool = True) -> int:
        """
        Get length of palindrome centered at position.

        Args:
            center: Center position in original string
            odd: True for odd-length, False for even-length (between center and center+1)

        Returns:
            Length of palindrome
        """
        with self._lock:
            self._stats.queries += 1

            if not self._string or center < 0 or center >= len(self._string):
                return 0

            # Convert to transformed index
            if odd:
                t_center = 2 * center + 2  # Points to the character
            else:
                t_center = 2 * center + 3  # Points to # between center and center+1

            if 0 < t_center < len(self._p) - 1:
                return self._p[t_center]

            return 0

    def is_palindrome(self, start: int, end: int) -> bool:
        """
        Check if substring [start, end] is a palindrome.

        Args:
            start: Start index
            end: End index (inclusive)

        Returns:
            True if palindrome
        """
        with self._lock:
            self._stats.queries += 1

            if start < 0 or end >= len(self._string) or start > end:
                return False

            length = end - start + 1
            center = (start + end) // 2

            if length % 2 == 1:  # Odd length
                radius = self.palindrome_at(center, odd=True)
                return radius >= length
            else:  # Even length
                radius = self.palindrome_at(start + length // 2 - 1, odd=False)
                return radius >= length

    def count_palindromes(self) -> int:
        """
        Count total palindromic substrings.

        Returns:
            Number of palindromes
        """
        with self._lock:
            return self._stats.total_palindromes

    def all_palindromes(self, min_length: int = 1) -> List[PalindromeInfo]:
        """
        Get all palindromic substrings.

        Args:
            min_length: Minimum length filter

        Returns:
            List of palindrome info
        """
        with self._lock:
            self._stats.queries += 1

            result = []
            n = len(self._string)

            for i in range(1, len(self._p) - 1):
                radius = self._p[i]

                # For each radius from 1 to max
                for r in range(1, radius + 1):
                    length = r
                    start = (i - r) // 2

                    if length >= min_length and start >= 0 and start + length <= n:
                        result.append(PalindromeInfo(
                            center=i // 2 if i % 2 == 0 else (i - 1) // 2,
                            length=length,
                            start=start,
                            end=start + length - 1,
                            text=self._string[start:start + length]
                        ))

            # Remove duplicates
            seen = set()
            unique = []
            for p in result:
                key = (p.start, p.length)
                if key not in seen:
                    seen.add(key)
                    unique.append(p)

            return sorted(unique, key=lambda p: (-p.length, p.start))

    def longest_palindrome_ending_at(self, pos: int) -> Optional[PalindromeInfo]:
        """
        Find longest palindrome ending at position.

        Args:
            pos: Position in string

        Returns:
            PalindromeInfo or None
        """
        with self._lock:
            self._stats.queries += 1

            if pos < 0 or pos >= len(self._string):
                return None

            max_len = 0
            max_start = pos

            # Check all possible centers
            for center in range(pos + 1):
                # Odd length
                radius = self.palindrome_at(center, odd=True)
                if center + radius // 2 >= pos:
                    length = (pos - center) * 2 + 1
                    start = center - (pos - center)
                    if start >= 0 and length > max_len:
                        max_len = length
                        max_start = start

                # Even length
                if center < pos:
                    radius = self.palindrome_at(center, odd=False)
                    if center + radius // 2 >= pos:
                        length = (pos - center) * 2
                        start = center - (pos - center) + 1
                        if start >= 0 and length > max_len:
                            max_len = length
                            max_start = start

            if max_len == 0:
                # Single character is always a palindrome
                return PalindromeInfo(
                    center=pos,
                    length=1,
                    start=pos,
                    end=pos,
                    text=self._string[pos]
                )

            return PalindromeInfo(
                center=(max_start + max_start + max_len - 1) // 2,
                length=max_len,
                start=max_start,
                end=max_start + max_len - 1,
                text=self._string[max_start:max_start + max_len]
            )

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def get_radii(self) -> List[int]:
        """Get the P array (palindrome radii)."""
        return self._p.copy()

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'string_length': self._stats.string_length,
            'longest_palindrome_length': self._stats.longest_palindrome_length,
            'total_palindromes': self._stats.total_palindromes,
            'queries': self._stats.queries
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_manacher() -> ManacherEngine:
    """Create empty Manacher engine."""
    return ManacherEngine()


def build_manacher(text: str) -> ManacherEngine:
    """
    Build Manacher engine from text.

    Args:
        text: Input string

    Returns:
        Built Manacher engine
    """
    engine = ManacherEngine()
    engine.build(text)
    return engine


def longest_palindrome(text: str) -> str:
    """
    Find longest palindromic substring.

    Args:
        text: Input string

    Returns:
        Longest palindrome
    """
    engine = build_manacher(text)
    return engine.longest_palindrome()


def count_palindromic_substrings(text: str) -> int:
    """
    Count palindromic substrings.

    Args:
        text: Input string

    Returns:
        Count of palindromes
    """
    engine = build_manacher(text)
    return engine.count_palindromes()


def is_palindrome(text: str) -> bool:
    """
    Check if entire string is palindrome.

    Args:
        text: Input string

    Returns:
        True if palindrome
    """
    engine = build_manacher(text)
    lp = engine.longest_palindrome()
    return len(lp) == len(text)
