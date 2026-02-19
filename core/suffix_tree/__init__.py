"""
BAEL Suffix Tree Engine
=======================

Suffix tree construction and operations.

"Ba'el indexes all suffixes in linear time." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger("BAEL.SuffixTree")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SuffixTreeNode:
    """Suffix tree node."""
    children: Dict[str, 'SuffixTreeNode'] = field(default_factory=dict)
    suffix_link: Optional['SuffixTreeNode'] = None
    start: int = 0
    end: Optional[int] = None  # None means leaf (uses global end)
    suffix_index: int = -1  # For leaves

    def edge_length(self, current_end: int) -> int:
        """Get edge length to this node."""
        return (self.end if self.end is not None else current_end) - self.start + 1


@dataclass
class SuffixTreeStats:
    """Suffix tree statistics."""
    text_length: int = 0
    node_count: int = 0
    leaf_count: int = 0
    internal_count: int = 0


# ============================================================================
# SUFFIX TREE - UKKONEN'S ALGORITHM
# ============================================================================

class SuffixTree:
    """
    Suffix tree using Ukkonen's algorithm.

    Features:
    - O(n) construction
    - Online (can extend)
    - Suffix links for efficiency

    "Ba'el builds the tree of all suffixes." — Ba'el
    """

    def __init__(self, text: str = ""):
        """Initialize suffix tree."""
        self._text = text + "$"  # Terminal symbol
        self._root = SuffixTreeNode()
        self._root.suffix_link = self._root

        self._size = len(self._text)
        self._global_end = -1
        self._remainder = 0

        self._active_node = self._root
        self._active_edge = -1
        self._active_length = 0

        self._stats = SuffixTreeStats()
        self._lock = threading.RLock()

        # Build tree
        if text:
            self._build()

        logger.debug(f"Suffix tree initialized for text of length {len(text)}")

    def _build(self) -> None:
        """Build suffix tree using Ukkonen's algorithm."""
        for i in range(self._size):
            self._extend(i)

    def _extend(self, pos: int) -> None:
        """Extend tree with character at position pos."""
        self._global_end = pos
        self._remainder += 1
        last_new_node = None

        while self._remainder > 0:
            if self._active_length == 0:
                self._active_edge = pos

            char = self._text[self._active_edge]

            if char not in self._active_node.children:
                # Create new leaf
                leaf = SuffixTreeNode(
                    start=pos,
                    suffix_index=pos - self._remainder + 1
                )
                self._active_node.children[char] = leaf

                if last_new_node is not None:
                    last_new_node.suffix_link = self._active_node
                    last_new_node = None
            else:
                next_node = self._active_node.children[char]
                edge_length = next_node.edge_length(self._global_end)

                if self._active_length >= edge_length:
                    # Walk down
                    self._active_edge += edge_length
                    self._active_length -= edge_length
                    self._active_node = next_node
                    continue

                # Check if character exists on edge
                if self._text[next_node.start + self._active_length] == self._text[pos]:
                    self._active_length += 1

                    if last_new_node is not None:
                        last_new_node.suffix_link = self._active_node
                    break

                # Split edge
                split = SuffixTreeNode(
                    start=next_node.start,
                    end=next_node.start + self._active_length - 1
                )
                self._active_node.children[char] = split

                # New leaf for current suffix
                leaf = SuffixTreeNode(
                    start=pos,
                    suffix_index=pos - self._remainder + 1
                )
                split.children[self._text[pos]] = leaf

                # Update original node
                next_node.start += self._active_length
                split.children[self._text[next_node.start]] = next_node

                if last_new_node is not None:
                    last_new_node.suffix_link = split

                last_new_node = split

            self._remainder -= 1

            if self._active_node == self._root and self._active_length > 0:
                self._active_length -= 1
                self._active_edge = pos - self._remainder + 1
            elif self._active_node != self._root:
                self._active_node = self._active_node.suffix_link or self._root

    def _set_suffix_indices(self, node: SuffixTreeNode, height: int) -> None:
        """Set suffix indices for all leaves."""
        if not node.children:
            node.suffix_index = self._size - height
            return

        for child in node.children.values():
            self._set_suffix_indices(
                child,
                height + child.edge_length(self._global_end)
            )

    def search(self, pattern: str) -> List[int]:
        """
        Search for pattern in text.

        Returns:
            List of starting positions
        """
        with self._lock:
            node = self._root
            i = 0

            while i < len(pattern):
                char = pattern[i]

                if char not in node.children:
                    return []

                child = node.children[char]
                edge_end = child.end if child.end is not None else self._global_end
                edge_start = child.start

                # Check edge characters
                j = edge_start
                while j <= edge_end and i < len(pattern):
                    if self._text[j] != pattern[i]:
                        return []
                    j += 1
                    i += 1

                if i < len(pattern):
                    node = child

            # Collect all suffix indices under this subtree
            return self._collect_indices(node if i == len(pattern) else child)

    def _collect_indices(self, node: SuffixTreeNode) -> List[int]:
        """Collect all suffix indices under a node."""
        indices = []

        if not node.children:
            if node.suffix_index >= 0 and node.suffix_index < self._size - 1:
                indices.append(node.suffix_index)
        else:
            for child in node.children.values():
                indices.extend(self._collect_indices(child))

        return sorted(indices)

    def contains(self, pattern: str) -> bool:
        """Check if pattern exists in text."""
        return len(self.search(pattern)) > 0

    def longest_repeated_substring(self) -> str:
        """
        Find longest repeated substring.

        Returns:
            Longest substring that appears more than once
        """
        with self._lock:
            result = ""

            def dfs(node: SuffixTreeNode, depth: int, path: str) -> None:
                nonlocal result

                if len(node.children) > 0:  # Internal node
                    for char, child in node.children.items():
                        edge_end = child.end if child.end is not None else self._global_end
                        edge_str = self._text[child.start:edge_end + 1]

                        new_depth = depth + len(edge_str)
                        new_path = path + edge_str

                        # Check if this node has multiple leaves below
                        leaf_count = self._count_leaves(child)
                        if leaf_count > 1 and new_depth > len(result):
                            result = new_path

                        dfs(child, new_depth, new_path)

            dfs(self._root, 0, "")

            # Remove terminal symbol if present
            if result.endswith("$"):
                result = result[:-1]

            return result

    def _count_leaves(self, node: SuffixTreeNode) -> int:
        """Count leaves under a node."""
        if not node.children:
            return 1

        return sum(self._count_leaves(child) for child in node.children.values())

    def longest_common_substring(self, other: str) -> str:
        """
        Find longest common substring with another string.

        Uses generalized suffix tree approach (simplified).
        """
        with self._lock:
            # Simple O(nm) approach for now
            # Could be optimized with proper generalized suffix tree
            text = self._text[:-1]  # Remove terminal
            best = ""

            for i in range(len(other)):
                for j in range(i + 1, len(other) + 1):
                    substring = other[i:j]
                    if len(substring) > len(best) and self.contains(substring):
                        best = substring

            return best

    def count_distinct_substrings(self) -> int:
        """
        Count distinct substrings.

        Sum of edge lengths over all edges.
        """
        with self._lock:
            count = 0

            def dfs(node: SuffixTreeNode) -> None:
                nonlocal count

                for child in node.children.values():
                    edge_length = child.edge_length(self._global_end)
                    count += edge_length
                    dfs(child)

            dfs(self._root)

            return count - 1  # Exclude terminal symbol


# ============================================================================
# GENERALIZED SUFFIX TREE
# ============================================================================

class GeneralizedSuffixTree:
    """
    Generalized suffix tree for multiple strings.

    "Ba'el unifies multiple texts into one tree." — Ba'el
    """

    def __init__(self):
        """Initialize generalized suffix tree."""
        self._texts: List[str] = []
        self._combined = ""
        self._tree: Optional[SuffixTree] = None
        self._separators: List[int] = []
        self._lock = threading.RLock()

    def add_text(self, text: str) -> int:
        """
        Add text to the tree.

        Returns:
            Index of the added text
        """
        with self._lock:
            idx = len(self._texts)
            self._texts.append(text)

            # Rebuild (simple approach)
            self._build()

            return idx

    def _build(self) -> None:
        """Build generalized suffix tree."""
        # Combine texts with unique separators
        parts = []
        self._separators = []
        pos = 0

        for i, text in enumerate(self._texts):
            parts.append(text)
            parts.append(chr(ord('#') + i))  # Unique separator
            self._separators.append(pos + len(text))
            pos += len(text) + 1

        self._combined = "".join(parts)
        self._tree = SuffixTree(self._combined[:-1])  # Remove last separator

    def longest_common_substring(self) -> str:
        """
        Find longest common substring among all texts.

        Returns:
            Longest common substring
        """
        with self._lock:
            if len(self._texts) < 2:
                return "" if len(self._texts) == 0 else self._texts[0]

            # Find nodes that have leaves from all texts
            best = ""

            def get_text_set(node: SuffixTreeNode) -> Set[int]:
                """Get set of text indices that have leaves under this node."""
                if not node.children:
                    # Find which text this suffix belongs to
                    if node.suffix_index >= 0:
                        idx = node.suffix_index
                        for i, sep in enumerate(self._separators):
                            if idx <= sep:
                                return {i}
                    return set()

                result = set()
                for child in node.children.values():
                    result |= get_text_set(child)
                return result

            def dfs(node: SuffixTreeNode, depth: int, path: str) -> None:
                nonlocal best

                if not node.children:
                    return

                for char, child in node.children.items():
                    if char in "#$%&":  # Skip separator edges
                        continue

                    edge_end = child.end if child.end is not None else self._tree._global_end
                    edge_str = self._tree._text[child.start:edge_end + 1]

                    # Remove any separator characters
                    clean_edge = ""
                    for c in edge_str:
                        if c not in "#$%&'":
                            clean_edge += c
                        else:
                            break

                    new_path = path + clean_edge

                    texts_present = get_text_set(child)
                    if len(texts_present) == len(self._texts):
                        if len(new_path) > len(best):
                            best = new_path

                    dfs(child, depth + len(clean_edge), new_path)

            if self._tree:
                dfs(self._tree._root, 0, "")

            return best

    def search_all(self, pattern: str) -> Dict[int, List[int]]:
        """
        Search for pattern in all texts.

        Returns:
            Dict mapping text index to list of positions
        """
        with self._lock:
            if not self._tree:
                return {}

            positions = self._tree.search(pattern)

            result: Dict[int, List[int]] = defaultdict(list)

            for pos in positions:
                # Find which text this position belongs to
                offset = 0
                for i, text in enumerate(self._texts):
                    if pos >= offset and pos < offset + len(text):
                        result[i].append(pos - offset)
                        break
                    offset += len(text) + 1  # +1 for separator

            return dict(result)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_suffix_tree(text: str) -> SuffixTree:
    """Create suffix tree for text."""
    return SuffixTree(text)


def create_generalized_suffix_tree() -> GeneralizedSuffixTree:
    """Create generalized suffix tree."""
    return GeneralizedSuffixTree()


def suffix_tree_search(text: str, pattern: str) -> List[int]:
    """Search for pattern using suffix tree."""
    tree = SuffixTree(text)
    return tree.search(pattern)


def longest_repeated_substring(text: str) -> str:
    """Find longest repeated substring."""
    tree = SuffixTree(text)
    return tree.longest_repeated_substring()


def longest_common_substring(texts: List[str]) -> str:
    """Find longest common substring among texts."""
    if len(texts) < 2:
        return texts[0] if texts else ""

    gst = GeneralizedSuffixTree()
    for text in texts:
        gst.add_text(text)

    return gst.longest_common_substring()


def count_distinct_substrings(text: str) -> int:
    """Count distinct substrings in text."""
    tree = SuffixTree(text)
    return tree.count_distinct_substrings()
