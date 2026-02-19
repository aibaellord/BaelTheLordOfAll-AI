"""
BAEL Aho-Corasick Automaton Engine
==================================

Multi-pattern string matching.

"Ba'el matches all patterns in a single pass." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger("BAEL.AhoCorasick")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ACMatch:
    """Match result."""
    position: int  # End position in text
    pattern_index: int
    pattern: str


@dataclass
class ACNode:
    """Aho-Corasick automaton node."""
    children: Dict[str, int] = field(default_factory=dict)
    fail: int = 0  # Failure link
    output: List[int] = field(default_factory=list)  # Pattern indices
    depth: int = 0


@dataclass
class ACStats:
    """Aho-Corasick statistics."""
    pattern_count: int = 0
    total_pattern_length: int = 0
    node_count: int = 0
    matches_found: int = 0
    texts_searched: int = 0


# ============================================================================
# AHO-CORASICK ENGINE
# ============================================================================

class AhoCorasickEngine:
    """
    Aho-Corasick Automaton for multi-pattern matching.

    Features:
    - O(n + m + z) matching (n=text, m=patterns, z=matches)
    - O(m) construction
    - All patterns matched in single pass
    - Failure links for efficiency

    "Ba'el weaves all patterns into one." — Ba'el
    """

    def __init__(self):
        """Initialize Aho-Corasick automaton."""
        self._nodes: List[ACNode] = [ACNode()]  # Root node
        self._patterns: List[str] = []
        self._built = False
        self._stats = ACStats()
        self._lock = threading.RLock()

        logger.debug("Aho-Corasick automaton initialized")

    # ========================================================================
    # BUILD
    # ========================================================================

    def add_pattern(self, pattern: str) -> int:
        """
        Add pattern to automaton.

        Args:
            pattern: Pattern string

        Returns:
            Pattern index
        """
        with self._lock:
            if self._built:
                raise RuntimeError("Cannot add patterns after build()")

            pattern_idx = len(self._patterns)
            self._patterns.append(pattern)

            self._stats.pattern_count += 1
            self._stats.total_pattern_length += len(pattern)

            # Add to trie
            node = 0  # Start at root

            for char in pattern:
                if char not in self._nodes[node].children:
                    # Create new node
                    new_node = ACNode(depth=self._nodes[node].depth + 1)
                    self._nodes.append(new_node)
                    self._nodes[node].children[char] = len(self._nodes) - 1
                    self._stats.node_count += 1

                node = self._nodes[node].children[char]

            # Mark pattern end
            self._nodes[node].output.append(pattern_idx)

            return pattern_idx

    def add_patterns(self, patterns: List[str]) -> List[int]:
        """
        Add multiple patterns.

        Args:
            patterns: List of pattern strings

        Returns:
            List of pattern indices
        """
        return [self.add_pattern(p) for p in patterns]

    def build(self) -> None:
        """Build failure links using BFS."""
        with self._lock:
            if self._built:
                return

            queue = deque()

            # Initialize failure links for depth-1 nodes
            for char, child in self._nodes[0].children.items():
                self._nodes[child].fail = 0
                queue.append(child)

            # BFS to build failure links
            while queue:
                node = queue.popleft()

                for char, child in self._nodes[node].children.items():
                    queue.append(child)

                    # Find failure link
                    fail = self._nodes[node].fail

                    while fail > 0 and char not in self._nodes[fail].children:
                        fail = self._nodes[fail].fail

                    if char in self._nodes[fail].children and self._nodes[fail].children[char] != child:
                        self._nodes[child].fail = self._nodes[fail].children[char]
                    else:
                        self._nodes[child].fail = 0

                    # Merge output lists
                    self._nodes[child].output.extend(
                        self._nodes[self._nodes[child].fail].output
                    )

            self._built = True
            self._stats.node_count = len(self._nodes)

            logger.info(
                f"AC automaton built: {self._stats.pattern_count} patterns, "
                f"{self._stats.node_count} nodes"
            )

    # ========================================================================
    # SEARCH
    # ========================================================================

    def search(self, text: str) -> List[ACMatch]:
        """
        Search for all pattern occurrences.

        Args:
            text: Text to search

        Returns:
            List of matches
        """
        with self._lock:
            if not self._built:
                self.build()

            self._stats.texts_searched += 1
            matches = []
            node = 0

            for i, char in enumerate(text):
                # Follow failure links until match or root
                while node > 0 and char not in self._nodes[node].children:
                    node = self._nodes[node].fail

                if char in self._nodes[node].children:
                    node = self._nodes[node].children[char]

                # Collect all matches at this position
                for pattern_idx in self._nodes[node].output:
                    pattern = self._patterns[pattern_idx]
                    matches.append(ACMatch(
                        position=i,
                        pattern_index=pattern_idx,
                        pattern=pattern
                    ))
                    self._stats.matches_found += 1

            return matches

    def search_first(self, text: str) -> Optional[ACMatch]:
        """
        Find first pattern occurrence.

        Args:
            text: Text to search

        Returns:
            First match or None
        """
        with self._lock:
            if not self._built:
                self.build()

            node = 0

            for i, char in enumerate(text):
                while node > 0 and char not in self._nodes[node].children:
                    node = self._nodes[node].fail

                if char in self._nodes[node].children:
                    node = self._nodes[node].children[char]

                if self._nodes[node].output:
                    pattern_idx = self._nodes[node].output[0]
                    return ACMatch(
                        position=i,
                        pattern_index=pattern_idx,
                        pattern=self._patterns[pattern_idx]
                    )

            return None

    def contains_any(self, text: str) -> bool:
        """Check if text contains any pattern."""
        return self.search_first(text) is not None

    def count_matches(self, text: str) -> int:
        """Count total pattern matches."""
        return len(self.search(text))

    def match_counts(self, text: str) -> Dict[int, int]:
        """
        Count matches per pattern.

        Args:
            text: Text to search

        Returns:
            Dict mapping pattern index to count
        """
        matches = self.search(text)
        counts: Dict[int, int] = {}

        for match in matches:
            counts[match.pattern_index] = counts.get(match.pattern_index, 0) + 1

        return counts

    def matched_patterns(self, text: str) -> Set[str]:
        """
        Get set of patterns found in text.

        Args:
            text: Text to search

        Returns:
            Set of matched patterns
        """
        matches = self.search(text)
        return {match.pattern for match in matches}

    # ========================================================================
    # STREAMING
    # ========================================================================

    def create_matcher(self) -> 'ACMatcher':
        """Create streaming matcher."""
        if not self._built:
            self.build()
        return ACMatcher(self)


class ACMatcher:
    """Streaming matcher for incremental processing."""

    def __init__(self, engine: AhoCorasickEngine):
        """
        Initialize matcher.

        Args:
            engine: Parent AC engine
        """
        self._engine = engine
        self._state = 0
        self._position = 0

    def feed(self, text: str) -> List[ACMatch]:
        """
        Feed text and get matches.

        Args:
            text: Text chunk

        Returns:
            Matches in this chunk
        """
        matches = []
        nodes = self._engine._nodes
        patterns = self._engine._patterns

        for char in text:
            while self._state > 0 and char not in nodes[self._state].children:
                self._state = nodes[self._state].fail

            if char in nodes[self._state].children:
                self._state = nodes[self._state].children[char]

            for pattern_idx in nodes[self._state].output:
                matches.append(ACMatch(
                    position=self._position,
                    pattern_index=pattern_idx,
                    pattern=patterns[pattern_idx]
                ))

            self._position += 1

        return matches

    def reset(self) -> None:
        """Reset matcher state."""
        self._state = 0
        self._position = 0


# ============================================================================
# UTILITIES
# ============================================================================

def create_aho_corasick() -> AhoCorasickEngine:
    """Create Aho-Corasick engine."""
    return AhoCorasickEngine()


def multi_pattern_search(
    text: str,
    patterns: List[str]
) -> List[ACMatch]:
    """
    Search for multiple patterns.

    Args:
        text: Text to search
        patterns: Patterns to find

    Returns:
        List of matches
    """
    engine = AhoCorasickEngine()
    engine.add_patterns(patterns)
    engine.build()
    return engine.search(text)


def contains_any_pattern(text: str, patterns: List[str]) -> bool:
    """Check if text contains any pattern."""
    engine = AhoCorasickEngine()
    engine.add_patterns(patterns)
    engine.build()
    return engine.contains_any(text)


def find_all_patterns(text: str, patterns: List[str]) -> Set[str]:
    """Find which patterns exist in text."""
    engine = AhoCorasickEngine()
    engine.add_patterns(patterns)
    engine.build()
    return engine.matched_patterns(text)
