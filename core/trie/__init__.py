"""
BAEL Trie/Prefix Tree Engine Implementation
=============================================

Efficient prefix-based data structure.

"Ba'el finds patterns in the chaos of characters." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, Generator, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.Trie")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class TrieNode:
    """A node in the trie."""

    __slots__ = ['children', 'is_end', 'value', 'count', 'metadata']

    def __init__(self):
        self.children: Dict[str, 'TrieNode'] = {}
        self.is_end: bool = False
        self.value: Any = None
        self.count: int = 0  # Number of words ending here
        self.metadata: Dict[str, Any] = {}

    def has_children(self) -> bool:
        return len(self.children) > 0


@dataclass
class SearchResult:
    """Result of a trie search."""
    key: str
    value: Any
    count: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# TRIE ENGINE
# ============================================================================

class Trie:
    """
    Trie (prefix tree) data structure.

    Features:
    - Prefix search
    - Auto-complete
    - Wildcard matching
    - Pattern matching

    "Ba'el organizes words with divine precision." — Ba'el
    """

    def __init__(self):
        """Initialize trie."""
        self._root = TrieNode()
        self._size = 0
        self._lock = threading.RLock()

        # Stats
        self._stats = {
            'inserts': 0,
            'searches': 0,
            'deletes': 0,
            'prefix_searches': 0
        }

        logger.info("Trie initialized")

    # ========================================================================
    # BASIC OPERATIONS
    # ========================================================================

    def insert(
        self,
        key: str,
        value: Any = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Insert a key into the trie.

        Args:
            key: Key to insert
            value: Optional value to store
            metadata: Optional metadata
        """
        if not key:
            return

        with self._lock:
            node = self._root

            for char in key:
                if char not in node.children:
                    node.children[char] = TrieNode()
                node = node.children[char]

            if not node.is_end:
                self._size += 1

            node.is_end = True
            node.value = value if value is not None else key
            node.count += 1

            if metadata:
                node.metadata.update(metadata)

            self._stats['inserts'] += 1

    def search(self, key: str) -> Optional[SearchResult]:
        """
        Search for exact key in trie.

        Args:
            key: Key to search

        Returns:
            SearchResult if found, None otherwise
        """
        with self._lock:
            self._stats['searches'] += 1

            node = self._find_node(key)

            if node and node.is_end:
                return SearchResult(
                    key=key,
                    value=node.value,
                    count=node.count,
                    metadata=node.metadata
                )

            return None

    def contains(self, key: str) -> bool:
        """Check if key exists."""
        result = self.search(key)
        return result is not None

    def get(self, key: str, default: Any = None) -> Any:
        """Get value for key."""
        result = self.search(key)
        return result.value if result else default

    def _find_node(self, key: str) -> Optional[TrieNode]:
        """Find node for key."""
        node = self._root

        for char in key:
            if char not in node.children:
                return None
            node = node.children[char]

        return node

    def delete(self, key: str) -> bool:
        """
        Delete a key from the trie.

        Args:
            key: Key to delete

        Returns:
            True if key was deleted
        """
        if not key:
            return False

        with self._lock:
            self._stats['deletes'] += 1

            # Find path to key
            path: List[Tuple[TrieNode, str]] = []
            node = self._root

            for char in key:
                if char not in node.children:
                    return False
                path.append((node, char))
                node = node.children[char]

            if not node.is_end:
                return False

            # Decrement count
            node.count -= 1

            if node.count > 0:
                return True

            # Mark as not end
            node.is_end = False
            node.value = None
            self._size -= 1

            # Clean up empty nodes
            if not node.has_children():
                for parent, char in reversed(path):
                    del parent.children[char]
                    if parent.is_end or parent.has_children():
                        break

            return True

    # ========================================================================
    # PREFIX OPERATIONS
    # ========================================================================

    def starts_with(self, prefix: str) -> bool:
        """
        Check if any key starts with prefix.

        Args:
            prefix: Prefix to check

        Returns:
            True if any key has this prefix
        """
        return self._find_node(prefix) is not None

    def find_by_prefix(
        self,
        prefix: str,
        max_results: int = 100
    ) -> List[SearchResult]:
        """
        Find all keys with given prefix.

        Args:
            prefix: Prefix to search
            max_results: Maximum results

        Returns:
            List of matching results
        """
        with self._lock:
            self._stats['prefix_searches'] += 1

            node = self._find_node(prefix)

            if not node:
                return []

            results = []
            self._collect_words(node, prefix, results, max_results)

            return results

    def _collect_words(
        self,
        node: TrieNode,
        prefix: str,
        results: List[SearchResult],
        max_results: int
    ) -> None:
        """Collect all words under a node."""
        if len(results) >= max_results:
            return

        if node.is_end:
            results.append(SearchResult(
                key=prefix,
                value=node.value,
                count=node.count,
                metadata=node.metadata
            ))

        for char, child in sorted(node.children.items()):
            if len(results) >= max_results:
                break
            self._collect_words(child, prefix + char, results, max_results)

    def autocomplete(
        self,
        prefix: str,
        max_results: int = 10
    ) -> List[str]:
        """
        Get autocomplete suggestions.

        Args:
            prefix: Prefix to complete
            max_results: Maximum suggestions

        Returns:
            List of suggested completions
        """
        results = self.find_by_prefix(prefix, max_results)
        # Sort by count (popularity)
        results.sort(key=lambda r: r.count, reverse=True)
        return [r.key for r in results[:max_results]]

    # ========================================================================
    # PATTERN MATCHING
    # ========================================================================

    def match_pattern(
        self,
        pattern: str,
        wildcard: str = '.',
        max_results: int = 100
    ) -> List[SearchResult]:
        """
        Match keys against pattern with wildcards.

        Args:
            pattern: Pattern with wildcards
            wildcard: Wildcard character (default '.')
            max_results: Maximum results

        Returns:
            List of matching results
        """
        results = []

        def dfs(node: TrieNode, index: int, current: str) -> None:
            if len(results) >= max_results:
                return

            if index == len(pattern):
                if node.is_end:
                    results.append(SearchResult(
                        key=current,
                        value=node.value,
                        count=node.count,
                        metadata=node.metadata
                    ))
                return

            char = pattern[index]

            if char == wildcard:
                # Match any character
                for c, child in node.children.items():
                    dfs(child, index + 1, current + c)
            else:
                # Match specific character
                if char in node.children:
                    dfs(node.children[char], index + 1, current + char)

        with self._lock:
            dfs(self._root, 0, "")

        return results

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def all_keys(self) -> Generator[str, None, None]:
        """Generate all keys in trie."""
        def traverse(node: TrieNode, prefix: str):
            if node.is_end:
                yield prefix
            for char, child in node.children.items():
                yield from traverse(child, prefix + char)

        with self._lock:
            yield from traverse(self._root, "")

    def count_by_prefix(self, prefix: str) -> int:
        """Count keys with given prefix."""
        node = self._find_node(prefix)
        if not node:
            return 0

        count = 0

        def count_words(n: TrieNode) -> None:
            nonlocal count
            if n.is_end:
                count += n.count
            for child in n.children.values():
                count_words(child)

        with self._lock:
            count_words(node)

        return count

    def longest_prefix(self, word: str) -> str:
        """
        Find longest matching prefix.

        Args:
            word: Word to check

        Returns:
            Longest prefix that exists in trie
        """
        with self._lock:
            node = self._root
            longest = ""
            current = ""

            for char in word:
                if char not in node.children:
                    break

                current += char
                node = node.children[char]

                if node.is_end:
                    longest = current

            return longest

    def shortest_prefix(self, word: str) -> Optional[str]:
        """
        Find shortest matching prefix.

        Args:
            word: Word to check

        Returns:
            Shortest prefix that exists in trie
        """
        with self._lock:
            node = self._root
            current = ""

            for char in word:
                if char not in node.children:
                    return None

                current += char
                node = node.children[char]

                if node.is_end:
                    return current

            return current if node.is_end else None

    # ========================================================================
    # STATS
    # ========================================================================

    def __len__(self) -> int:
        return self._size

    def __contains__(self, key: str) -> bool:
        return self.contains(key)

    def get_stats(self) -> Dict[str, Any]:
        """Get trie statistics."""
        return {
            'size': self._size,
            **self._stats
        }


# ============================================================================
# RADIX TRIE (COMPRESSED)
# ============================================================================

class RadixTrieNode:
    """Node in a radix trie (compressed)."""

    __slots__ = ['key', 'children', 'is_end', 'value']

    def __init__(self, key: str = ""):
        self.key = key
        self.children: Dict[str, 'RadixTrieNode'] = {}
        self.is_end: bool = False
        self.value: Any = None


class RadixTrie:
    """
    Radix trie (compressed trie).

    More memory efficient than standard trie.
    """

    def __init__(self):
        self._root = RadixTrieNode()
        self._size = 0
        self._lock = threading.RLock()

    def insert(self, key: str, value: Any = None) -> None:
        """Insert key into radix trie."""
        if not key:
            return

        with self._lock:
            node = self._root
            remaining = key

            while remaining:
                # Find matching child
                match = None
                match_len = 0

                for edge_key, child in node.children.items():
                    # Find common prefix length
                    i = 0
                    while (i < len(edge_key) and
                           i < len(remaining) and
                           edge_key[i] == remaining[i]):
                        i += 1

                    if i > 0:
                        match = (edge_key, child)
                        match_len = i
                        break

                if match:
                    edge_key, child = match

                    if match_len == len(edge_key):
                        # Full match, continue down
                        remaining = remaining[match_len:]
                        node = child
                    else:
                        # Partial match, split node
                        new_node = RadixTrieNode(edge_key[:match_len])
                        child.key = edge_key[match_len:]

                        del node.children[edge_key]
                        node.children[edge_key[:match_len]] = new_node
                        new_node.children[edge_key[match_len:]] = child

                        remaining = remaining[match_len:]
                        node = new_node
                else:
                    # No match, create new node
                    new_node = RadixTrieNode(remaining)
                    new_node.is_end = True
                    new_node.value = value if value is not None else key
                    node.children[remaining] = new_node
                    self._size += 1
                    return

            # Reached end
            if not node.is_end:
                self._size += 1
            node.is_end = True
            node.value = value if value is not None else key

    def search(self, key: str) -> Optional[Any]:
        """Search for key."""
        with self._lock:
            node = self._root
            remaining = key

            while remaining:
                match = None

                for edge_key, child in node.children.items():
                    if remaining.startswith(edge_key):
                        match = child
                        remaining = remaining[len(edge_key):]
                        break

                if match:
                    node = match
                else:
                    return None

            return node.value if node.is_end else None

    def __len__(self) -> int:
        return self._size


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_trie() -> Trie:
    """Create a new trie."""
    return Trie()


def create_radix_trie() -> RadixTrie:
    """Create a new radix trie."""
    return RadixTrie()
