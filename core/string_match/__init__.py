"""
BAEL String Matching Engine Implementation
===========================================

Advanced string matching algorithms.

"Ba'el finds all patterns hidden in the cosmos." — Ba'el
"""

import logging
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import functools

logger = logging.getLogger("BAEL.StringMatch")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class MatchAlgorithm(Enum):
    """String matching algorithms."""
    NAIVE = "naive"
    KMP = "kmp"
    RABIN_KARP = "rabin_karp"
    BOYER_MOORE = "boyer_moore"
    Z_ALGORITHM = "z_algorithm"
    AHO_CORASICK = "aho_corasick"


@dataclass
class MatchResult:
    """Match result."""
    pattern: str
    positions: List[int]
    count: int
    algorithm: MatchAlgorithm


@dataclass
class StringMatchConfig:
    """String matching configuration."""
    algorithm: MatchAlgorithm = MatchAlgorithm.KMP
    case_sensitive: bool = True
    prime: int = 101  # For Rabin-Karp


# ============================================================================
# KMP ALGORITHM
# ============================================================================

class KMPMatcher:
    """
    Knuth-Morris-Pratt string matching.

    Features:
    - O(n + m) time complexity
    - Failure function preprocessing
    - No backtracking in text

    "Ba'el never backtracks in the pursuit of truth." — Ba'el
    """

    def __init__(self, pattern: str):
        """
        Initialize KMP matcher.

        Args:
            pattern: Pattern to search for
        """
        self.pattern = pattern
        self.m = len(pattern)
        self.failure = self._compute_failure()

    def _compute_failure(self) -> List[int]:
        """Compute failure function (partial match table)."""
        failure = [0] * self.m

        if self.m == 0:
            return failure

        j = 0

        for i in range(1, self.m):
            while j > 0 and self.pattern[i] != self.pattern[j]:
                j = failure[j - 1]

            if self.pattern[i] == self.pattern[j]:
                j += 1

            failure[i] = j

        return failure

    def search(self, text: str) -> List[int]:
        """
        Search for pattern in text.

        Args:
            text: Text to search in

        Returns:
            List of match positions
        """
        if self.m == 0 or len(text) < self.m:
            return []

        positions = []
        j = 0

        for i in range(len(text)):
            while j > 0 and text[i] != self.pattern[j]:
                j = self.failure[j - 1]

            if text[i] == self.pattern[j]:
                j += 1

            if j == self.m:
                positions.append(i - self.m + 1)
                j = self.failure[j - 1]

        return positions

    def contains(self, text: str) -> bool:
        """Check if pattern exists in text."""
        matches = self.search(text)
        return len(matches) > 0


# ============================================================================
# RABIN-KARP ALGORITHM
# ============================================================================

class RabinKarpMatcher:
    """
    Rabin-Karp string matching with rolling hash.

    Features:
    - O(n + m) expected time
    - Rolling hash for efficiency
    - Good for multiple pattern matching

    "Ba'el computes hashes of infinite strings." — Ba'el
    """

    def __init__(self, pattern: str, prime: int = 101, base: int = 256):
        """
        Initialize Rabin-Karp matcher.

        Args:
            pattern: Pattern to search for
            prime: Prime for hashing
            base: Base for hashing (typically 256 for ASCII)
        """
        self.pattern = pattern
        self.m = len(pattern)
        self.prime = prime
        self.base = base

        # Precompute pattern hash and h = base^(m-1) % prime
        self.pattern_hash = self._hash(pattern)

        self.h = 1
        for _ in range(self.m - 1):
            self.h = (self.h * self.base) % self.prime

    def _hash(self, s: str) -> int:
        """Compute hash of string."""
        h = 0
        for c in s:
            h = (h * self.base + ord(c)) % self.prime
        return h

    def search(self, text: str) -> List[int]:
        """
        Search for pattern in text.

        Args:
            text: Text to search in

        Returns:
            List of match positions
        """
        n = len(text)

        if self.m == 0 or n < self.m:
            return []

        positions = []

        # Initial hash of first window
        text_hash = self._hash(text[:self.m])

        for i in range(n - self.m + 1):
            # Check hash match
            if text_hash == self.pattern_hash:
                # Verify actual match
                if text[i:i + self.m] == self.pattern:
                    positions.append(i)

            # Roll hash to next window
            if i < n - self.m:
                text_hash = (
                    (text_hash - ord(text[i]) * self.h) * self.base +
                    ord(text[i + self.m])
                ) % self.prime

                if text_hash < 0:
                    text_hash += self.prime

        return positions


# ============================================================================
# BOYER-MOORE ALGORITHM
# ============================================================================

class BoyerMooreMatcher:
    """
    Boyer-Moore string matching.

    Features:
    - O(n/m) best case (sublinear!)
    - Bad character and good suffix rules
    - Best for large alphabets

    "Ba'el skips through irrelevant realities." — Ba'el
    """

    def __init__(self, pattern: str):
        """
        Initialize Boyer-Moore matcher.

        Args:
            pattern: Pattern to search for
        """
        self.pattern = pattern
        self.m = len(pattern)

        # Bad character table
        self.bad_char = self._compute_bad_char()

        # Good suffix table (simplified)
        self.good_suffix = self._compute_good_suffix()

    def _compute_bad_char(self) -> Dict[str, int]:
        """Compute bad character table."""
        bad_char = {}

        for i in range(self.m):
            bad_char[self.pattern[i]] = i

        return bad_char

    def _compute_good_suffix(self) -> List[int]:
        """Compute good suffix table (simplified version)."""
        good_suffix = [self.m] * (self.m + 1)

        # Simplified: just use pattern length
        return good_suffix

    def search(self, text: str) -> List[int]:
        """
        Search for pattern in text.

        Args:
            text: Text to search in

        Returns:
            List of match positions
        """
        n = len(text)

        if self.m == 0 or n < self.m:
            return []

        positions = []
        i = 0

        while i <= n - self.m:
            j = self.m - 1

            # Match from right to left
            while j >= 0 and self.pattern[j] == text[i + j]:
                j -= 1

            if j < 0:
                # Match found
                positions.append(i)
                i += 1  # Move by 1 (simplified)
            else:
                # Bad character rule
                bad_char_shift = j - self.bad_char.get(text[i + j], -1)

                i += max(1, bad_char_shift)

        return positions


# ============================================================================
# Z ALGORITHM
# ============================================================================

class ZAlgorithmMatcher:
    """
    Z-Algorithm string matching.

    Features:
    - O(n + m) time complexity
    - Z-array computation
    - Simple and efficient

    "Ba'el computes all Z-values instantaneously." — Ba'el
    """

    def __init__(self, pattern: str):
        """
        Initialize Z-Algorithm matcher.

        Args:
            pattern: Pattern to search for
        """
        self.pattern = pattern
        self.m = len(pattern)

    def _compute_z_array(self, s: str) -> List[int]:
        """Compute Z-array for string."""
        n = len(s)
        z = [0] * n

        if n == 0:
            return z

        z[0] = n
        l, r = 0, 0

        for i in range(1, n):
            if i > r:
                l, r = i, i

                while r < n and s[r - l] == s[r]:
                    r += 1

                z[i] = r - l
                r -= 1
            else:
                k = i - l

                if z[k] < r - i + 1:
                    z[i] = z[k]
                else:
                    l = i

                    while r < n and s[r - l] == s[r]:
                        r += 1

                    z[i] = r - l
                    r -= 1

        return z

    def search(self, text: str) -> List[int]:
        """
        Search for pattern in text.

        Args:
            text: Text to search in

        Returns:
            List of match positions
        """
        if self.m == 0 or len(text) < self.m:
            return []

        # Concatenate pattern + separator + text
        concat = self.pattern + '\x00' + text
        z = self._compute_z_array(concat)

        positions = []

        for i in range(self.m + 1, len(concat)):
            if z[i] == self.m:
                positions.append(i - self.m - 1)

        return positions

    def z_array(self, s: str) -> List[int]:
        """Get Z-array for string."""
        return self._compute_z_array(s)


# ============================================================================
# AHO-CORASICK ALGORITHM
# ============================================================================

class AhoCorasickNode:
    """Node in Aho-Corasick automaton."""

    def __init__(self):
        self.children: Dict[str, 'AhoCorasickNode'] = {}
        self.failure: Optional['AhoCorasickNode'] = None
        self.output: List[int] = []  # Pattern indices


class AhoCorasickMatcher:
    """
    Aho-Corasick multi-pattern matching.

    Features:
    - O(n + m + z) where z is number of matches
    - Multiple pattern matching
    - Finite automaton

    "Ba'el matches all patterns simultaneously." — Ba'el
    """

    def __init__(self, patterns: List[str]):
        """
        Initialize Aho-Corasick matcher.

        Args:
            patterns: List of patterns to search for
        """
        self.patterns = patterns
        self.root = AhoCorasickNode()

        self._build_trie()
        self._build_failure_links()

    def _build_trie(self) -> None:
        """Build trie from patterns."""
        for i, pattern in enumerate(self.patterns):
            node = self.root

            for c in pattern:
                if c not in node.children:
                    node.children[c] = AhoCorasickNode()
                node = node.children[c]

            node.output.append(i)

    def _build_failure_links(self) -> None:
        """Build failure links using BFS."""
        from collections import deque

        queue = deque()

        # Initialize depth 1 nodes
        for child in self.root.children.values():
            child.failure = self.root
            queue.append(child)

        while queue:
            current = queue.popleft()

            for c, child in current.children.items():
                queue.append(child)

                failure = current.failure

                while failure is not None and c not in failure.children:
                    failure = failure.failure

                if failure is None:
                    child.failure = self.root
                else:
                    child.failure = failure.children[c]
                    child.output.extend(child.failure.output)

    def search(self, text: str) -> Dict[str, List[int]]:
        """
        Search for all patterns in text.

        Args:
            text: Text to search in

        Returns:
            Dict of pattern -> list of positions
        """
        result: Dict[str, List[int]] = {p: [] for p in self.patterns}

        node = self.root

        for i, c in enumerate(text):
            while node is not None and c not in node.children:
                node = node.failure

            if node is None:
                node = self.root
                continue

            node = node.children[c]

            for pattern_idx in node.output:
                pattern = self.patterns[pattern_idx]
                position = i - len(pattern) + 1
                result[pattern].append(position)

        return result


# ============================================================================
# STRING MATCHING ENGINE
# ============================================================================

class StringMatchEngine:
    """
    Unified string matching engine.

    "Ba'el finds all needles in all haystacks." — Ba'el
    """

    def __init__(self, config: Optional[StringMatchConfig] = None):
        """Initialize engine."""
        self.config = config or StringMatchConfig()
        self._lock = threading.RLock()

        logger.info(f"String match engine initialized ({self.config.algorithm.value})")

    def search(
        self,
        text: str,
        pattern: str,
        algorithm: Optional[MatchAlgorithm] = None
    ) -> MatchResult:
        """
        Search for pattern in text.

        Args:
            text: Text to search in
            pattern: Pattern to find
            algorithm: Algorithm to use

        Returns:
            MatchResult
        """
        algo = algorithm or self.config.algorithm

        # Handle case sensitivity
        search_text = text if self.config.case_sensitive else text.lower()
        search_pattern = pattern if self.config.case_sensitive else pattern.lower()

        if algo == MatchAlgorithm.KMP:
            matcher = KMPMatcher(search_pattern)
            positions = matcher.search(search_text)
        elif algo == MatchAlgorithm.RABIN_KARP:
            matcher = RabinKarpMatcher(search_pattern, self.config.prime)
            positions = matcher.search(search_text)
        elif algo == MatchAlgorithm.BOYER_MOORE:
            matcher = BoyerMooreMatcher(search_pattern)
            positions = matcher.search(search_text)
        elif algo == MatchAlgorithm.Z_ALGORITHM:
            matcher = ZAlgorithmMatcher(search_pattern)
            positions = matcher.search(search_text)
        else:
            # Naive fallback
            positions = []
            for i in range(len(search_text) - len(search_pattern) + 1):
                if search_text[i:i + len(search_pattern)] == search_pattern:
                    positions.append(i)

        return MatchResult(
            pattern=pattern,
            positions=positions,
            count=len(positions),
            algorithm=algo
        )

    def search_multiple(
        self,
        text: str,
        patterns: List[str]
    ) -> Dict[str, List[int]]:
        """
        Search for multiple patterns (Aho-Corasick).

        Args:
            text: Text to search in
            patterns: Patterns to find

        Returns:
            Dict of pattern -> positions
        """
        search_text = text if self.config.case_sensitive else text.lower()
        search_patterns = patterns if self.config.case_sensitive else [p.lower() for p in patterns]

        matcher = AhoCorasickMatcher(search_patterns)
        result = matcher.search(search_text)

        # Map back to original patterns
        return {patterns[i]: result[search_patterns[i]] for i in range(len(patterns))}

    def count(self, text: str, pattern: str) -> int:
        """Count occurrences of pattern."""
        result = self.search(text, pattern)
        return result.count

    def contains(self, text: str, pattern: str) -> bool:
        """Check if pattern exists."""
        return self.count(text, pattern) > 0


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_string_matcher(
    algorithm: MatchAlgorithm = MatchAlgorithm.KMP
) -> StringMatchEngine:
    """Create string matching engine."""
    return StringMatchEngine(StringMatchConfig(algorithm=algorithm))


def kmp_search(text: str, pattern: str) -> List[int]:
    """Quick KMP search."""
    return KMPMatcher(pattern).search(text)


def rabin_karp_search(text: str, pattern: str) -> List[int]:
    """Quick Rabin-Karp search."""
    return RabinKarpMatcher(pattern).search(text)


def multi_pattern_search(text: str, patterns: List[str]) -> Dict[str, List[int]]:
    """Quick multi-pattern search."""
    return AhoCorasickMatcher(patterns).search(text)


def count_occurrences(text: str, pattern: str) -> int:
    """Count pattern occurrences."""
    return len(KMPMatcher(pattern).search(text))
