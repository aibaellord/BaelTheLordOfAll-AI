"""
BAEL Suffix Array Engine Implementation
=========================================

String searching with O(n log n) construction.

"Ba'el indexes all suffixes of reality." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.SuffixArray")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SuffixArrayStats:
    """Suffix array statistics."""
    text_length: int = 0
    search_count: int = 0
    pattern_matches: int = 0


# ============================================================================
# SUFFIX ARRAY ENGINE
# ============================================================================

class SuffixArrayEngine:
    """
    Suffix Array implementation.

    Features:
    - O(n log n) construction
    - O(m log n) pattern search
    - LCP array for advanced queries
    - Multiple pattern support

    "Ba'el indexes every suffix of all strings." — Ba'el
    """

    def __init__(self, text: str):
        """
        Initialize suffix array.

        Args:
            text: Text to index
        """
        self._text = text
        self._n = len(text)

        # Suffix array
        self._sa: List[int] = []

        # LCP array (longest common prefix between consecutive suffixes)
        self._lcp: List[int] = []

        # Inverse suffix array (position of each suffix in sorted order)
        self._rank: List[int] = []

        self._stats = SuffixArrayStats(text_length=self._n)
        self._lock = threading.RLock()

        # Build arrays
        self._build_suffix_array()
        self._build_lcp_array()

        logger.info(f"Suffix array initialized (length={self._n})")

    def _build_suffix_array(self) -> None:
        """Build suffix array using prefix doubling."""
        if self._n == 0:
            return

        # Initial ranking by first character
        self._rank = [ord(c) for c in self._text]
        self._sa = list(range(self._n))

        k = 1
        while k < self._n:
            # Sort by (rank[i], rank[i + k])
            self._sa.sort(key=lambda i: (
                self._rank[i],
                self._rank[i + k] if i + k < self._n else -1
            ))

            # Update ranks
            new_rank = [0] * self._n

            for i in range(1, self._n):
                prev = self._sa[i - 1]
                curr = self._sa[i]

                prev_pair = (
                    self._rank[prev],
                    self._rank[prev + k] if prev + k < self._n else -1
                )
                curr_pair = (
                    self._rank[curr],
                    self._rank[curr + k] if curr + k < self._n else -1
                )

                if curr_pair != prev_pair:
                    new_rank[curr] = new_rank[prev] + 1
                else:
                    new_rank[curr] = new_rank[prev]

            self._rank = new_rank
            k *= 2

    def _build_lcp_array(self) -> None:
        """Build LCP array using Kasai's algorithm."""
        if self._n == 0:
            return

        self._lcp = [0] * self._n

        # Compute inverse suffix array
        inv_sa = [0] * self._n
        for i, suffix_pos in enumerate(self._sa):
            inv_sa[suffix_pos] = i

        k = 0
        for i in range(self._n):
            if inv_sa[i] == 0:
                k = 0
                continue

            j = self._sa[inv_sa[i] - 1]

            while i + k < self._n and j + k < self._n and self._text[i + k] == self._text[j + k]:
                k += 1

            self._lcp[inv_sa[i]] = k

            if k > 0:
                k -= 1

    # ========================================================================
    # PATTERN SEARCH
    # ========================================================================

    def search(self, pattern: str) -> List[int]:
        """
        Search for pattern occurrences.

        Args:
            pattern: Pattern to search

        Returns:
            List of starting positions
        """
        if not pattern or self._n == 0:
            return []

        with self._lock:
            self._stats.search_count += 1

            # Binary search for leftmost occurrence
            left = self._lower_bound(pattern)

            if left == -1:
                return []

            # Binary search for rightmost occurrence
            right = self._upper_bound(pattern)

            # Collect all occurrences
            result = sorted(self._sa[left:right + 1])

            self._stats.pattern_matches += len(result)

            return result

    def _lower_bound(self, pattern: str) -> int:
        """Find leftmost suffix >= pattern."""
        m = len(pattern)
        lo, hi = 0, self._n - 1
        result = -1

        while lo <= hi:
            mid = (lo + hi) // 2
            suffix = self._text[self._sa[mid]:]

            if suffix[:m] >= pattern:
                result = mid
                hi = mid - 1
            else:
                lo = mid + 1

        # Verify it's actually a match
        if result != -1:
            suffix = self._text[self._sa[result]:]
            if not suffix.startswith(pattern):
                return -1

        return result

    def _upper_bound(self, pattern: str) -> int:
        """Find rightmost suffix with pattern prefix."""
        m = len(pattern)
        lo, hi = 0, self._n - 1
        result = -1

        while lo <= hi:
            mid = (lo + hi) // 2
            suffix = self._text[self._sa[mid]:]

            if suffix[:m] <= pattern:
                if suffix.startswith(pattern):
                    result = mid
                lo = mid + 1
            else:
                hi = mid - 1

        return result

    def count(self, pattern: str) -> int:
        """
        Count pattern occurrences.

        Args:
            pattern: Pattern to count

        Returns:
            Number of occurrences
        """
        return len(self.search(pattern))

    def contains(self, pattern: str) -> bool:
        """
        Check if pattern exists.

        Args:
            pattern: Pattern to check

        Returns:
            True if pattern exists
        """
        if not pattern:
            return True

        with self._lock:
            left = self._lower_bound(pattern)
            return left != -1

    # ========================================================================
    # LCP QUERIES
    # ========================================================================

    def longest_repeated_substring(self) -> str:
        """
        Find longest repeated substring.

        Returns:
            Longest repeated substring
        """
        if self._n <= 1:
            return ""

        max_lcp = 0
        max_idx = 0

        for i in range(1, self._n):
            if self._lcp[i] > max_lcp:
                max_lcp = self._lcp[i]
                max_idx = i

        if max_lcp == 0:
            return ""

        start = self._sa[max_idx]
        return self._text[start:start + max_lcp]

    def longest_common_prefix(self, i: int, j: int) -> int:
        """
        Find longest common prefix of suffixes at positions i and j.

        Args:
            i: First suffix position
            j: Second suffix position

        Returns:
            LCP length
        """
        if i < 0 or i >= self._n or j < 0 or j >= self._n:
            return 0

        if i == j:
            return self._n - i

        # Get ranks
        inv_sa = [0] * self._n
        for idx, pos in enumerate(self._sa):
            inv_sa[pos] = idx

        ri, rj = inv_sa[i], inv_sa[j]

        if ri > rj:
            ri, rj = rj, ri

        # Minimum LCP in range [ri+1, rj]
        return min(self._lcp[ri + 1:rj + 1]) if ri + 1 <= rj else 0

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def get_suffix(self, rank: int) -> str:
        """
        Get suffix at given rank.

        Args:
            rank: Rank in sorted order

        Returns:
            Suffix string
        """
        if rank < 0 or rank >= self._n:
            return ""

        return self._text[self._sa[rank]:]

    @property
    def suffix_array(self) -> List[int]:
        """Get suffix array."""
        return self._sa.copy()

    @property
    def lcp_array(self) -> List[int]:
        """Get LCP array."""
        return self._lcp.copy()

    @property
    def text(self) -> str:
        """Get indexed text."""
        return self._text

    def __len__(self) -> int:
        return self._n

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'text_length': self._stats.text_length,
            'search_count': self._stats.search_count,
            'pattern_matches': self._stats.pattern_matches
        }


# ============================================================================
# SUFFIX AUTOMATON
# ============================================================================

class SuffixAutomatonState:
    """State in suffix automaton."""

    def __init__(self):
        self.transitions: Dict[str, int] = {}
        self.link: int = -1
        self.length: int = 0
        self.is_terminal: bool = False


class SuffixAutomaton:
    """
    Suffix Automaton (DAWG) implementation.

    Features:
    - O(n) construction
    - O(m) pattern matching
    - Compact representation

    "Ba'el constructs the minimal automaton of all suffixes." — Ba'el
    """

    def __init__(self, text: str = ""):
        """
        Initialize suffix automaton.

        Args:
            text: Initial text
        """
        self._states: List[SuffixAutomatonState] = [SuffixAutomatonState()]
        self._last = 0

        self._lock = threading.RLock()

        for c in text:
            self._extend(c)

        logger.info(f"Suffix automaton initialized (states={len(self._states)})")

    def _extend(self, c: str) -> None:
        """Extend automaton by one character."""
        cur = len(self._states)
        self._states.append(SuffixAutomatonState())
        self._states[cur].length = self._states[self._last].length + 1

        p = self._last

        while p != -1 and c not in self._states[p].transitions:
            self._states[p].transitions[c] = cur
            p = self._states[p].link

        if p == -1:
            self._states[cur].link = 0
        else:
            q = self._states[p].transitions[c]

            if self._states[p].length + 1 == self._states[q].length:
                self._states[cur].link = q
            else:
                clone = len(self._states)
                self._states.append(SuffixAutomatonState())
                self._states[clone].length = self._states[p].length + 1
                self._states[clone].transitions = self._states[q].transitions.copy()
                self._states[clone].link = self._states[q].link

                while p != -1 and self._states[p].transitions.get(c) == q:
                    self._states[p].transitions[c] = clone
                    p = self._states[p].link

                self._states[q].link = clone
                self._states[cur].link = clone

        self._last = cur

    def add(self, text: str) -> None:
        """
        Add text to automaton.

        Args:
            text: Text to add
        """
        with self._lock:
            for c in text:
                self._extend(c)

    def contains(self, pattern: str) -> bool:
        """
        Check if pattern is a substring.

        Args:
            pattern: Pattern to check

        Returns:
            True if pattern exists
        """
        with self._lock:
            state = 0

            for c in pattern:
                if c not in self._states[state].transitions:
                    return False
                state = self._states[state].transitions[c]

            return True

    def count_distinct_substrings(self) -> int:
        """
        Count distinct substrings.

        Returns:
            Number of distinct substrings
        """
        total = 0

        for state in self._states[1:]:
            total += state.length - self._states[state.link].length

        return total

    @property
    def state_count(self) -> int:
        """Get number of states."""
        return len(self._states)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_suffix_array(text: str) -> SuffixArrayEngine:
    """Create suffix array for text."""
    return SuffixArrayEngine(text)


def create_suffix_automaton(text: str = "") -> SuffixAutomaton:
    """Create suffix automaton for text."""
    return SuffixAutomaton(text)


def find_all_occurrences(text: str, pattern: str) -> List[int]:
    """
    Find all occurrences of pattern in text.

    Args:
        text: Text to search
        pattern: Pattern to find

    Returns:
        List of starting positions
    """
    sa = SuffixArrayEngine(text)
    return sa.search(pattern)


def longest_repeated_substring(text: str) -> str:
    """
    Find longest repeated substring.

    Args:
        text: Input text

    Returns:
        Longest repeated substring
    """
    sa = SuffixArrayEngine(text)
    return sa.longest_repeated_substring()


def count_distinct_substrings(text: str) -> int:
    """
    Count distinct substrings.

    Args:
        text: Input text

    Returns:
        Number of distinct substrings
    """
    sam = SuffixAutomaton(text)
    return sam.count_distinct_substrings()
