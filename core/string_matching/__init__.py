"""
BAEL Advanced String Matching Engine
====================================

Comprehensive string matching algorithms.

"Ba'el finds all patterns in the text." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple, Iterator
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger("BAEL.StringMatching")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class MatchResult:
    """String match result."""
    positions: List[int] = field(default_factory=list)
    count: int = 0
    pattern: str = ""


@dataclass
class MatchStats:
    """String matching statistics."""
    text_length: int = 0
    pattern_length: int = 0
    comparisons: int = 0
    matches_found: int = 0


# ============================================================================
# KMP (KNUTH-MORRIS-PRATT)
# ============================================================================

class KMPMatcher:
    """
    Knuth-Morris-Pratt string matching.

    Features:
    - O(n + m) time complexity
    - Failure function preprocessing
    - No backtracking in text

    "Ba'el never revisits text positions." — Ba'el
    """

    def __init__(self, pattern: str):
        """Initialize KMP with pattern."""
        self._pattern = pattern
        self._failure = self._compute_failure(pattern)
        self._stats = MatchStats()
        self._lock = threading.RLock()

        logger.debug(f"KMP initialized with pattern length {len(pattern)}")

    def _compute_failure(self, pattern: str) -> List[int]:
        """
        Compute failure function.

        failure[i] = length of longest proper prefix of pattern[0:i+1]
                     that is also a suffix
        """
        m = len(pattern)
        if m == 0:
            return []

        failure = [0] * m
        j = 0

        for i in range(1, m):
            while j > 0 and pattern[i] != pattern[j]:
                j = failure[j - 1]

            if pattern[i] == pattern[j]:
                j += 1

            failure[i] = j

        return failure

    def search(self, text: str) -> List[int]:
        """
        Search for pattern in text.

        Args:
            text: Text to search in

        Returns:
            List of starting positions of matches
        """
        with self._lock:
            matches = []
            m = len(self._pattern)
            n = len(text)

            if m == 0 or m > n:
                return matches

            j = 0
            comparisons = 0

            for i in range(n):
                comparisons += 1

                while j > 0 and text[i] != self._pattern[j]:
                    j = self._failure[j - 1]
                    comparisons += 1

                if text[i] == self._pattern[j]:
                    j += 1

                if j == m:
                    matches.append(i - m + 1)
                    j = self._failure[j - 1]

            self._stats.text_length = n
            self._stats.pattern_length = m
            self._stats.comparisons = comparisons
            self._stats.matches_found = len(matches)

            return matches

    def get_failure_function(self) -> List[int]:
        """Get the failure function array."""
        return self._failure.copy()

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'text_length': self._stats.text_length,
            'pattern_length': self._stats.pattern_length,
            'comparisons': self._stats.comparisons,
            'matches_found': self._stats.matches_found
        }


# ============================================================================
# RABIN-KARP
# ============================================================================

class RabinKarpMatcher:
    """
    Rabin-Karp string matching using rolling hash.

    Features:
    - O(n + m) expected time
    - O(nm) worst case (hash collisions)
    - Good for multiple pattern search

    "Ba'el uses the power of hashing." — Ba'el
    """

    def __init__(self, pattern: str, base: int = 256, prime: int = 101):
        """
        Initialize Rabin-Karp.

        Args:
            pattern: Pattern to search for
            base: Hash base (typically alphabet size)
            prime: Prime for modular arithmetic
        """
        self._pattern = pattern
        self._base = base
        self._prime = prime
        self._pattern_hash = self._compute_hash(pattern)
        self._stats = MatchStats()
        self._lock = threading.RLock()

    def _compute_hash(self, s: str) -> int:
        """Compute hash of string."""
        h = 0
        for c in s:
            h = (h * self._base + ord(c)) % self._prime
        return h

    def search(self, text: str) -> List[int]:
        """
        Search for pattern in text.

        Returns:
            List of starting positions
        """
        with self._lock:
            matches = []
            m = len(self._pattern)
            n = len(text)

            if m == 0 or m > n:
                return matches

            # Precompute base^(m-1) mod prime
            h = pow(self._base, m - 1, self._prime)

            # Initial hash of text window
            text_hash = self._compute_hash(text[:m])
            comparisons = m

            for i in range(n - m + 1):
                # Check hash match
                if text_hash == self._pattern_hash:
                    # Verify actual match
                    comparisons += m
                    if text[i:i + m] == self._pattern:
                        matches.append(i)

                # Roll hash forward
                if i < n - m:
                    text_hash = (self._base * (text_hash - ord(text[i]) * h) +
                               ord(text[i + m])) % self._prime
                    if text_hash < 0:
                        text_hash += self._prime

            self._stats.text_length = n
            self._stats.pattern_length = m
            self._stats.comparisons = comparisons
            self._stats.matches_found = len(matches)

            return matches

    def search_multiple(self, text: str, patterns: List[str]) -> Dict[str, List[int]]:
        """
        Search for multiple patterns.

        Rabin-Karp is efficient for multiple patterns of same length.

        Returns:
            Dict mapping pattern to list of positions
        """
        with self._lock:
            results = {p: [] for p in patterns}

            if not patterns:
                return results

            # Group patterns by length
            by_length: Dict[int, List[str]] = defaultdict(list)
            for p in patterns:
                by_length[len(p)].append(p)

            n = len(text)

            for m, pats in by_length.items():
                if m == 0 or m > n:
                    continue

                # Compute pattern hashes
                pat_hashes = {self._compute_hash(p): p for p in pats}

                h = pow(self._base, m - 1, self._prime)
                text_hash = self._compute_hash(text[:m])

                for i in range(n - m + 1):
                    if text_hash in pat_hashes:
                        substring = text[i:i + m]
                        if substring in results:
                            results[substring].append(i)

                    if i < n - m:
                        text_hash = (self._base * (text_hash - ord(text[i]) * h) +
                                   ord(text[i + m])) % self._prime
                        if text_hash < 0:
                            text_hash += self._prime

            return results


# ============================================================================
# BOYER-MOORE
# ============================================================================

class BoyerMooreMatcher:
    """
    Boyer-Moore string matching.

    Features:
    - O(n/m) best case (sublinear!)
    - Bad character + good suffix rules
    - Right-to-left pattern comparison

    "Ba'el skips ahead with wisdom." — Ba'el
    """

    def __init__(self, pattern: str):
        """Initialize Boyer-Moore with pattern."""
        self._pattern = pattern
        self._bad_char = self._compute_bad_char(pattern)
        self._good_suffix = self._compute_good_suffix(pattern)
        self._stats = MatchStats()
        self._lock = threading.RLock()

    def _compute_bad_char(self, pattern: str) -> Dict[str, int]:
        """
        Compute bad character table.

        Maps character to rightmost position in pattern.
        """
        table = {}
        for i, c in enumerate(pattern):
            table[c] = i
        return table

    def _compute_good_suffix(self, pattern: str) -> List[int]:
        """
        Compute good suffix table.

        shift[i] = how far to shift if mismatch at position i
        """
        m = len(pattern)
        if m == 0:
            return []

        shift = [m] * m
        border = [0] * (m + 1)

        # Case 1: matching suffix exists in pattern
        i = m
        j = m + 1
        border[i] = j

        while i > 0:
            while j <= m and pattern[i - 1] != pattern[j - 1]:
                if shift[j - 1] == m:
                    shift[j - 1] = j - i
                j = border[j]

            i -= 1
            j -= 1
            border[i] = j

        # Case 2: partial match with prefix
        j = border[0]
        for i in range(m):
            if shift[i] == m:
                shift[i] = j
            if i == j:
                j = border[j]

        return shift

    def search(self, text: str) -> List[int]:
        """
        Search for pattern in text.

        Returns:
            List of starting positions
        """
        with self._lock:
            matches = []
            m = len(self._pattern)
            n = len(text)

            if m == 0 or m > n:
                return matches

            comparisons = 0
            i = 0

            while i <= n - m:
                j = m - 1

                while j >= 0 and self._pattern[j] == text[i + j]:
                    j -= 1
                    comparisons += 1

                if j < 0:
                    matches.append(i)
                    i += self._good_suffix[0] if m > 0 else 1
                else:
                    comparisons += 1

                    # Bad character shift
                    bad_shift = j - self._bad_char.get(text[i + j], -1)

                    # Good suffix shift
                    good_shift = self._good_suffix[j] if j < len(self._good_suffix) else 1

                    i += max(bad_shift, good_shift, 1)

            self._stats.text_length = n
            self._stats.pattern_length = m
            self._stats.comparisons = comparisons
            self._stats.matches_found = len(matches)

            return matches


# ============================================================================
# Z-ALGORITHM (ALREADY EXISTS BUT COMPREHENSIVE VERSION)
# ============================================================================

class ZAlgorithm:
    """
    Z-Algorithm for pattern matching.

    Features:
    - O(n + m) time
    - Z-array construction
    - Useful for multiple applications

    "Ba'el computes Z values efficiently." — Ba'el
    """

    def __init__(self):
        """Initialize Z-Algorithm."""
        self._stats = MatchStats()
        self._lock = threading.RLock()

    def compute_z_array(self, s: str) -> List[int]:
        """
        Compute Z-array for string.

        z[i] = length of longest substring starting at i
               that matches a prefix of s
        """
        n = len(s)
        if n == 0:
            return []

        z = [0] * n
        z[0] = n

        l, r = 0, 0

        for i in range(1, n):
            if i < r:
                z[i] = min(r - i, z[i - l])

            while i + z[i] < n and s[z[i]] == s[i + z[i]]:
                z[i] += 1

            if i + z[i] > r:
                l, r = i, i + z[i]

        return z

    def search(self, text: str, pattern: str) -> List[int]:
        """
        Search for pattern using Z-algorithm.

        Returns:
            List of starting positions
        """
        with self._lock:
            if not pattern or len(pattern) > len(text):
                return []

            # Concatenate pattern$text
            concat = pattern + "$" + text
            z = self.compute_z_array(concat)

            m = len(pattern)
            matches = []

            for i in range(m + 1, len(concat)):
                if z[i] == m:
                    matches.append(i - m - 1)

            return matches


# ============================================================================
# AHO-CORASICK (MULTI-PATTERN)
# ============================================================================

class AhoCorasick:
    """
    Aho-Corasick multi-pattern matching.

    Features:
    - O(n + m + z) where z is total matches
    - Trie with failure links
    - Finds all patterns in single pass

    "Ba'el finds all patterns at once." — Ba'el
    """

    def __init__(self):
        """Initialize Aho-Corasick."""
        self._goto: List[Dict[str, int]] = [{}]
        self._fail: List[int] = [0]
        self._output: List[List[str]] = [[]]
        self._built = False
        self._lock = threading.RLock()

    def add_pattern(self, pattern: str) -> None:
        """Add pattern to the automaton."""
        with self._lock:
            self._built = False
            state = 0

            for c in pattern:
                if c not in self._goto[state]:
                    self._goto[state][c] = len(self._goto)
                    self._goto.append({})
                    self._fail.append(0)
                    self._output.append([])

                state = self._goto[state][c]

            self._output[state].append(pattern)

    def build(self) -> None:
        """Build failure links."""
        with self._lock:
            if self._built:
                return

            from collections import deque

            queue = deque()

            # Initialize depth-1 states
            for c, s in self._goto[0].items():
                self._fail[s] = 0
                queue.append(s)

            # BFS to build failure links
            while queue:
                r = queue.popleft()

                for c, s in self._goto[r].items():
                    queue.append(s)

                    state = self._fail[r]
                    while state != 0 and c not in self._goto[state]:
                        state = self._fail[state]

                    self._fail[s] = self._goto[state].get(c, 0)

                    if self._fail[s] != s:
                        self._output[s] = self._output[s] + self._output[self._fail[s]]

            self._built = True

    def search(self, text: str) -> Dict[str, List[int]]:
        """
        Search for all patterns in text.

        Returns:
            Dict mapping pattern to list of ending positions
        """
        self.build()

        with self._lock:
            results: Dict[str, List[int]] = defaultdict(list)
            state = 0

            for i, c in enumerate(text):
                while state != 0 and c not in self._goto[state]:
                    state = self._fail[state]

                state = self._goto[state].get(c, 0)

                for pattern in self._output[state]:
                    results[pattern].append(i - len(pattern) + 1)

            return dict(results)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_kmp(pattern: str) -> KMPMatcher:
    """Create KMP matcher."""
    return KMPMatcher(pattern)


def create_rabin_karp(pattern: str) -> RabinKarpMatcher:
    """Create Rabin-Karp matcher."""
    return RabinKarpMatcher(pattern)


def create_boyer_moore(pattern: str) -> BoyerMooreMatcher:
    """Create Boyer-Moore matcher."""
    return BoyerMooreMatcher(pattern)


def create_z_algorithm() -> ZAlgorithm:
    """Create Z-algorithm engine."""
    return ZAlgorithm()


def create_aho_corasick() -> AhoCorasick:
    """Create Aho-Corasick automaton."""
    return AhoCorasick()


def kmp_search(text: str, pattern: str) -> List[int]:
    """KMP search for pattern in text."""
    return KMPMatcher(pattern).search(text)


def rabin_karp_search(text: str, pattern: str) -> List[int]:
    """Rabin-Karp search for pattern in text."""
    return RabinKarpMatcher(pattern).search(text)


def boyer_moore_search(text: str, pattern: str) -> List[int]:
    """Boyer-Moore search for pattern in text."""
    return BoyerMooreMatcher(pattern).search(text)


def multi_pattern_search(text: str, patterns: List[str]) -> Dict[str, List[int]]:
    """Search for multiple patterns using Aho-Corasick."""
    ac = AhoCorasick()
    for p in patterns:
        ac.add_pattern(p)
    return ac.search(text)


def count_occurrences(text: str, pattern: str) -> int:
    """Count pattern occurrences in text."""
    return len(kmp_search(text, pattern))
