"""
BAEL Palindrome Tree (Eertree) Engine
=====================================

Efficient palindrome substring handling.

"Ba'el finds symmetry in all strings." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("BAEL.PalindromeTree")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class PalindromeNode:
    """Node in palindrome tree (represents a palindrome)."""
    length: int
    suffix_link: int = -1  # Longest proper palindromic suffix
    edges: Dict[str, int] = field(default_factory=dict)  # char -> node_id
    count: int = 0  # Number of occurrences
    start_positions: List[int] = field(default_factory=list)


@dataclass
class PalindromeTreeStats:
    """Palindrome tree statistics."""
    total_palindromes: int = 0  # Distinct palindromes
    total_occurrences: int = 0
    longest_palindrome: int = 0
    string_length: int = 0


# ============================================================================
# PALINDROME TREE ENGINE
# ============================================================================

class PalindromeTreeEngine:
    """
    Palindrome Tree (Eertree) for palindrome substring queries.

    Features:
    - O(n) construction for string of length n
    - O(n) total distinct palindromes
    - Count occurrences of each palindrome
    - Find longest palindromic substring

    "Ba'el sees the mirror in all words." — Ba'el
    """

    def __init__(self):
        """Initialize palindrome tree."""
        # Node 0: "imaginary" node of length -1 (for building odd palindromes)
        # Node 1: empty string of length 0 (for building even palindromes)
        self._nodes: List[PalindromeNode] = [
            PalindromeNode(length=-1, suffix_link=0),  # Root for odd
            PalindromeNode(length=0, suffix_link=0),   # Root for even
        ]

        self._string = ""
        self._last_suffix = 1  # Last added suffix (starts at even root)
        self._stats = PalindromeTreeStats()
        self._lock = threading.RLock()

        logger.debug("Palindrome tree initialized")

    def _get_node(self, idx: int) -> PalindromeNode:
        """Get node by index."""
        return self._nodes[idx]

    def _add_node(self, length: int, suffix_link: int = -1) -> int:
        """Add new node and return its index."""
        idx = len(self._nodes)
        self._nodes.append(PalindromeNode(length=length, suffix_link=suffix_link))
        self._stats.total_palindromes += 1

        if length > self._stats.longest_palindrome:
            self._stats.longest_palindrome = length

        return idx

    def _find_suffix_palindrome(self, idx: int, pos: int) -> int:
        """
        Find suffix palindrome that can be extended.

        Start from node idx and follow suffix links until
        we find a palindrome that can be extended with s[pos].
        """
        while True:
            node = self._get_node(idx)

            # Check if we can extend this palindrome
            # Need character at position pos - length - 1 to match s[pos]
            prev_pos = pos - node.length - 1

            if prev_pos >= 0 and self._string[prev_pos] == self._string[pos]:
                return idx

            # Follow suffix link
            if idx == 0:
                return idx  # Can't go further

            idx = node.suffix_link

    # ========================================================================
    # BUILD
    # ========================================================================

    def add_char(self, char: str) -> int:
        """
        Add character to the tree.

        Args:
            char: Character to add

        Returns:
            Index of the node representing longest palindrome ending here
        """
        with self._lock:
            pos = len(self._string)
            self._string += char
            self._stats.string_length += 1

            # Find palindrome to extend
            cur = self._find_suffix_palindrome(self._last_suffix, pos)
            cur_node = self._get_node(cur)

            if char in cur_node.edges:
                # Palindrome already exists
                self._last_suffix = cur_node.edges[char]
                self._nodes[self._last_suffix].count += 1
                self._nodes[self._last_suffix].start_positions.append(
                    pos - self._nodes[self._last_suffix].length + 1
                )
                self._stats.total_occurrences += 1
                return self._last_suffix

            # Create new node
            new_len = cur_node.length + 2
            new_idx = self._add_node(new_len)
            cur_node.edges[char] = new_idx

            self._nodes[new_idx].count = 1
            self._nodes[new_idx].start_positions.append(pos - new_len + 1)
            self._stats.total_occurrences += 1

            # Find suffix link for new node
            if new_len == 1:
                # Single character palindrome
                self._nodes[new_idx].suffix_link = 1
            else:
                # Find longest proper palindromic suffix
                suffix_parent = self._find_suffix_palindrome(
                    cur_node.suffix_link, pos
                )
                self._nodes[new_idx].suffix_link = \
                    self._get_node(suffix_parent).edges.get(char, 1)

            self._last_suffix = new_idx
            return new_idx

    def build(self, text: str) -> None:
        """
        Build palindrome tree from string.

        Args:
            text: Input string
        """
        with self._lock:
            # Reset
            self._nodes = [
                PalindromeNode(length=-1, suffix_link=0),
                PalindromeNode(length=0, suffix_link=0),
            ]
            self._string = ""
            self._last_suffix = 1
            self._stats = PalindromeTreeStats()

            # Add each character
            for char in text:
                self.add_char(char)

            # Propagate counts through suffix links
            self._propagate_counts()

            logger.info(
                f"Palindrome tree built: {len(text)} chars, "
                f"{self._stats.total_palindromes} distinct palindromes"
            )

    def _propagate_counts(self) -> None:
        """Propagate counts through suffix links."""
        # Process nodes in reverse order (by when they were added)
        for i in range(len(self._nodes) - 1, 1, -1):
            node = self._nodes[i]
            if node.suffix_link > 1:
                self._nodes[node.suffix_link].count += node.count

    # ========================================================================
    # QUERIES
    # ========================================================================

    def get_distinct_count(self) -> int:
        """Get number of distinct palindromes."""
        return self._stats.total_palindromes

    def get_total_occurrences(self) -> int:
        """Get total palindrome occurrences."""
        return self._stats.total_occurrences

    def get_longest_length(self) -> int:
        """Get length of longest palindrome."""
        return self._stats.longest_palindrome

    def get_palindrome(self, node_idx: int) -> str:
        """
        Get palindrome string for a node.

        Args:
            node_idx: Node index

        Returns:
            Palindrome string
        """
        with self._lock:
            if node_idx < 0 or node_idx >= len(self._nodes):
                return ""

            node = self._nodes[node_idx]

            if node.length <= 0:
                return ""

            if not node.start_positions:
                return ""

            start = node.start_positions[0]
            return self._string[start:start + node.length]

    def get_all_palindromes(self) -> List[Tuple[str, int]]:
        """
        Get all distinct palindromes with counts.

        Returns:
            List of (palindrome, count) tuples
        """
        with self._lock:
            result = []

            for i in range(2, len(self._nodes)):
                node = self._nodes[i]
                palindrome = self.get_palindrome(i)

                if palindrome:
                    result.append((palindrome, node.count))

            return result

    def find_palindrome(self, palindrome: str) -> Optional[int]:
        """
        Find node for a palindrome if it exists.

        Args:
            palindrome: Palindrome to find

        Returns:
            Node index or None
        """
        with self._lock:
            if not palindrome:
                return 1  # Empty palindrome

            # Start from appropriate root
            length = len(palindrome)

            if length == 1:
                # Single char - start from odd root
                if palindrome in self._nodes[0].edges:
                    return self._nodes[0].edges[palindrome]
                return None

            # Try to find by walking the tree
            # This is O(n) - could be optimized with hash
            for i in range(2, len(self._nodes)):
                if self.get_palindrome(i) == palindrome:
                    return i

            return None

    def count_palindrome(self, palindrome: str) -> int:
        """
        Count occurrences of a specific palindrome.

        Args:
            palindrome: Palindrome to count

        Returns:
            Number of occurrences
        """
        node_idx = self.find_palindrome(palindrome)

        if node_idx is None:
            return 0

        return self._nodes[node_idx].count

    def get_palindromes_ending_at(self, pos: int) -> List[str]:
        """
        Get all palindromes ending at position.

        Args:
            pos: Position in string (0-indexed)

        Returns:
            List of palindromes
        """
        with self._lock:
            if pos < 0 or pos >= len(self._string):
                return []

            result = []

            # Rebuild to position pos to find ending palindromes
            # This is O(n) - better implementation would track during build
            for i in range(2, len(self._nodes)):
                node = self._nodes[i]

                for start in node.start_positions:
                    if start + node.length - 1 == pos:
                        result.append(self._string[start:start + node.length])

            return result

    def longest_palindrome(self) -> str:
        """
        Get longest palindromic substring.

        Returns:
            Longest palindrome
        """
        with self._lock:
            max_len = 0
            max_palindrome = ""

            for i in range(2, len(self._nodes)):
                node = self._nodes[i]

                if node.length > max_len and node.start_positions:
                    max_len = node.length
                    start = node.start_positions[0]
                    max_palindrome = self._string[start:start + node.length]

            return max_palindrome

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
            'distinct_palindromes': self._stats.total_palindromes,
            'total_occurrences': self._stats.total_occurrences,
            'longest_palindrome': self._stats.longest_palindrome,
            'node_count': len(self._nodes)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_palindrome_tree() -> PalindromeTreeEngine:
    """Create empty palindrome tree."""
    return PalindromeTreeEngine()


def build_palindrome_tree(text: str) -> PalindromeTreeEngine:
    """
    Build palindrome tree from text.

    Args:
        text: Input string

    Returns:
        Built palindrome tree
    """
    tree = PalindromeTreeEngine()
    tree.build(text)
    return tree


def count_distinct_palindromes(text: str) -> int:
    """
    Count distinct palindromic substrings.

    Args:
        text: Input string

    Returns:
        Number of distinct palindromes
    """
    tree = build_palindrome_tree(text)
    return tree.get_distinct_count()


def longest_palindrome(text: str) -> str:
    """
    Find longest palindromic substring.

    Args:
        text: Input string

    Returns:
        Longest palindrome
    """
    tree = build_palindrome_tree(text)
    return tree.longest_palindrome()


def get_all_palindromes(text: str) -> List[str]:
    """
    Get all distinct palindromic substrings.

    Args:
        text: Input string

    Returns:
        List of palindromes
    """
    tree = build_palindrome_tree(text)
    return [p for p, _ in tree.get_all_palindromes()]
