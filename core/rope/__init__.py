"""
BAEL Rope Engine Implementation
=================================

Efficient string manipulation for large texts.

"Ba'el ties all strings together with perfect rope." — Ba'el
"""

import logging
import random
import threading
from typing import Any, Dict, Iterator, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("BAEL.Rope")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class RopeConfig:
    """Rope configuration."""
    leaf_size: int = 512  # Max characters in leaf
    rebalance_threshold: float = 2.0  # Rebalance if depth > log2(length) * threshold


class RopeNode:
    """Node in rope tree."""

    def __init__(self, text: Optional[str] = None):
        """Initialize node."""
        self.left: Optional['RopeNode'] = None
        self.right: Optional['RopeNode'] = None

        # Only leaves have text
        self.text = text

        # Cached values
        self._length: Optional[int] = None
        self._depth: Optional[int] = None

    @property
    def is_leaf(self) -> bool:
        """Check if node is a leaf."""
        return self.text is not None

    @property
    def length(self) -> int:
        """Get total length of subtree."""
        if self._length is not None:
            return self._length

        if self.is_leaf:
            self._length = len(self.text)
        else:
            left_len = self.left.length if self.left else 0
            right_len = self.right.length if self.right else 0
            self._length = left_len + right_len

        return self._length

    @property
    def depth(self) -> int:
        """Get depth of subtree."""
        if self._depth is not None:
            return self._depth

        if self.is_leaf:
            self._depth = 0
        else:
            left_depth = self.left.depth if self.left else 0
            right_depth = self.right.depth if self.right else 0
            self._depth = 1 + max(left_depth, right_depth)

        return self._depth

    def invalidate_cache(self) -> None:
        """Invalidate cached values."""
        self._length = None
        self._depth = None


@dataclass
class RopeStats:
    """Rope statistics."""
    length: int = 0
    node_count: int = 0
    leaf_count: int = 0
    depth: int = 0
    concat_count: int = 0
    split_count: int = 0


# ============================================================================
# ROPE ENGINE
# ============================================================================

class RopeEngine:
    """
    Rope data structure for efficient string manipulation.

    Features:
    - O(log n) concatenation
    - O(log n) split
    - O(log n) insert/delete
    - O(m + log n) substring

    "Ba'el weaves all texts into a perfect rope." — Ba'el
    """

    def __init__(
        self,
        text: str = "",
        config: Optional[RopeConfig] = None
    ):
        """
        Initialize rope.

        Args:
            text: Initial text
            config: Configuration
        """
        self.config = config or RopeConfig()
        self._lock = threading.RLock()

        self._stats = RopeStats()

        if text:
            self.root = self._build(text)
        else:
            self.root = None

        logger.info(f"Rope initialized (length={len(text)})")

    def _build(self, text: str) -> Optional[RopeNode]:
        """Build rope from text."""
        if not text:
            return None

        if len(text) <= self.config.leaf_size:
            self._stats.leaf_count += 1
            self._stats.node_count += 1
            return RopeNode(text)

        mid = len(text) // 2

        node = RopeNode()
        node.left = self._build(text[:mid])
        node.right = self._build(text[mid:])

        self._stats.node_count += 1

        return node

    # ========================================================================
    # BASIC OPERATIONS
    # ========================================================================

    def __len__(self) -> int:
        """Get total length."""
        return self.root.length if self.root else 0

    def __str__(self) -> str:
        """Convert to string."""
        return self.to_string()

    def to_string(self) -> str:
        """Convert entire rope to string."""
        if self.root is None:
            return ""

        result: List[str] = []
        self._collect(self.root, result)
        return "".join(result)

    def _collect(self, node: RopeNode, result: List[str]) -> None:
        """Collect text from subtree."""
        if node.is_leaf:
            result.append(node.text)
        else:
            if node.left:
                self._collect(node.left, result)
            if node.right:
                self._collect(node.right, result)

    def __getitem__(self, key):
        """Get character or substring."""
        if isinstance(key, int):
            return self.char_at(key)
        elif isinstance(key, slice):
            start, stop, step = key.indices(len(self))
            if step != 1:
                # Fallback for non-unit steps
                return self.to_string()[key]
            return self.substring(start, stop)
        else:
            raise TypeError(f"Invalid index type: {type(key)}")

    def char_at(self, index: int) -> str:
        """
        Get character at index.

        Args:
            index: Index (0-based)

        Returns:
            Character
        """
        if self.root is None:
            raise IndexError("Rope is empty")

        length = len(self)

        if index < 0:
            index += length

        if index < 0 or index >= length:
            raise IndexError(f"Index {index} out of range")

        with self._lock:
            return self._char_at(self.root, index)

    def _char_at(self, node: RopeNode, index: int) -> str:
        """Get character from subtree."""
        if node.is_leaf:
            return node.text[index]

        left_len = node.left.length if node.left else 0

        if index < left_len:
            return self._char_at(node.left, index)
        else:
            return self._char_at(node.right, index - left_len)

    def substring(self, start: int, end: int) -> str:
        """
        Get substring [start, end).

        Args:
            start: Start index (inclusive)
            end: End index (exclusive)

        Returns:
            Substring
        """
        if self.root is None:
            return ""

        length = len(self)

        start = max(0, start)
        end = min(length, end)

        if start >= end:
            return ""

        with self._lock:
            result: List[str] = []
            self._substring(self.root, start, end, 0, result)
            return "".join(result)

    def _substring(
        self,
        node: RopeNode,
        start: int,
        end: int,
        offset: int,
        result: List[str]
    ) -> None:
        """Collect substring from subtree."""
        if start >= end:
            return

        if node.is_leaf:
            local_start = max(0, start - offset)
            local_end = min(len(node.text), end - offset)

            if local_start < local_end:
                result.append(node.text[local_start:local_end])
        else:
            left_len = node.left.length if node.left else 0

            if start < offset + left_len and node.left:
                self._substring(node.left, start, end, offset, result)

            if end > offset + left_len and node.right:
                self._substring(node.right, start, end, offset + left_len, result)

    # ========================================================================
    # CONCATENATION
    # ========================================================================

    def concat(self, other: 'RopeEngine') -> 'RopeEngine':
        """
        Concatenate with another rope.

        Args:
            other: Rope to concatenate

        Returns:
            New concatenated rope
        """
        with self._lock:
            result = RopeEngine(config=self.config)

            if self.root is None:
                result.root = other.root
            elif other.root is None:
                result.root = self.root
            else:
                result.root = RopeNode()
                result.root.left = self.root
                result.root.right = other.root

                self._stats.concat_count += 1

            return result

    def __add__(self, other: 'RopeEngine') -> 'RopeEngine':
        """Concatenation operator."""
        return self.concat(other)

    def append(self, text: str) -> None:
        """
        Append text to end.

        Args:
            text: Text to append
        """
        if not text:
            return

        other = RopeEngine(text, self.config)

        with self._lock:
            if self.root is None:
                self.root = other.root
            else:
                new_root = RopeNode()
                new_root.left = self.root
                new_root.right = other.root
                self.root = new_root

                self._stats.concat_count += 1

    def prepend(self, text: str) -> None:
        """
        Prepend text to beginning.

        Args:
            text: Text to prepend
        """
        if not text:
            return

        other = RopeEngine(text, self.config)

        with self._lock:
            if self.root is None:
                self.root = other.root
            else:
                new_root = RopeNode()
                new_root.left = other.root
                new_root.right = self.root
                self.root = new_root

                self._stats.concat_count += 1

    # ========================================================================
    # SPLIT
    # ========================================================================

    def split(self, index: int) -> Tuple['RopeEngine', 'RopeEngine']:
        """
        Split rope at index.

        Args:
            index: Split position

        Returns:
            (left_rope, right_rope)
        """
        with self._lock:
            self._stats.split_count += 1

            if self.root is None or index <= 0:
                return RopeEngine(config=self.config), self._copy()

            if index >= len(self):
                return self._copy(), RopeEngine(config=self.config)

            left_root, right_root = self._split(self.root, index)

            left = RopeEngine(config=self.config)
            left.root = left_root

            right = RopeEngine(config=self.config)
            right.root = right_root

            return left, right

    def _split(
        self,
        node: RopeNode,
        index: int
    ) -> Tuple[Optional[RopeNode], Optional[RopeNode]]:
        """Split subtree at index."""
        if node.is_leaf:
            if index <= 0:
                return None, RopeNode(node.text)
            elif index >= len(node.text):
                return RopeNode(node.text), None
            else:
                return RopeNode(node.text[:index]), RopeNode(node.text[index:])

        left_len = node.left.length if node.left else 0

        if index <= left_len:
            left_left, left_right = self._split(node.left, index) if node.left else (None, None)

            if left_right or node.right:
                new_right = RopeNode()
                new_right.left = left_right
                new_right.right = node.right
            else:
                new_right = None

            return left_left, new_right
        else:
            right_left, right_right = self._split(node.right, index - left_len) if node.right else (None, None)

            if node.left or right_left:
                new_left = RopeNode()
                new_left.left = node.left
                new_left.right = right_left
            else:
                new_left = None

            return new_left, right_right

    def _copy(self) -> 'RopeEngine':
        """Create a shallow copy."""
        result = RopeEngine(config=self.config)
        result.root = self.root
        return result

    # ========================================================================
    # INSERT / DELETE
    # ========================================================================

    def insert(self, index: int, text: str) -> None:
        """
        Insert text at index.

        Args:
            index: Insertion position
            text: Text to insert
        """
        if not text:
            return

        with self._lock:
            left, right = self.split(index)
            middle = RopeEngine(text, self.config)

            self.root = left.concat(middle).concat(right).root

    def delete(self, start: int, end: int) -> str:
        """
        Delete text in range [start, end).

        Args:
            start: Start index
            end: End index

        Returns:
            Deleted text
        """
        deleted = self.substring(start, end)

        with self._lock:
            left, _ = self.split(start)
            _, right = self.split(end)

            self.root = left.concat(right).root

        return deleted

    def replace(self, start: int, end: int, text: str) -> str:
        """
        Replace text in range [start, end) with new text.

        Args:
            start: Start index
            end: End index
            text: Replacement text

        Returns:
            Replaced text
        """
        deleted = self.substring(start, end)

        with self._lock:
            left, _ = self.split(start)
            _, right = self.split(end)

            if text:
                middle = RopeEngine(text, self.config)
                self.root = left.concat(middle).concat(right).root
            else:
                self.root = left.concat(right).root

        return deleted

    # ========================================================================
    # SEARCH
    # ========================================================================

    def find(self, pattern: str, start: int = 0) -> int:
        """
        Find first occurrence of pattern.

        Args:
            pattern: Pattern to find
            start: Start position

        Returns:
            Index or -1 if not found
        """
        if not pattern:
            return start

        # Simple approach: convert to string and search
        # For production, use a more efficient algorithm
        text = self.to_string()
        return text.find(pattern, start)

    def find_all(self, pattern: str) -> List[int]:
        """
        Find all occurrences of pattern.

        Args:
            pattern: Pattern to find

        Returns:
            List of indices
        """
        if not pattern:
            return []

        text = self.to_string()
        result = []
        start = 0

        while True:
            idx = text.find(pattern, start)
            if idx == -1:
                break
            result.append(idx)
            start = idx + 1

        return result

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def __iter__(self) -> Iterator[str]:
        """Iterate over characters."""
        if self.root:
            yield from self._iter_chars(self.root)

    def _iter_chars(self, node: RopeNode) -> Iterator[str]:
        """Iterate characters in subtree."""
        if node.is_leaf:
            yield from node.text
        else:
            if node.left:
                yield from self._iter_chars(node.left)
            if node.right:
                yield from self._iter_chars(node.right)

    def lines(self) -> List[str]:
        """Split into lines."""
        return self.to_string().split('\n')

    def line_count(self) -> int:
        """Count number of lines."""
        return self.to_string().count('\n') + 1

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'length': len(self),
            'depth': self.root.depth if self.root else 0,
            'concat_count': self._stats.concat_count,
            'split_count': self._stats.split_count
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_rope(text: str = "") -> RopeEngine:
    """Create a new rope."""
    return RopeEngine(text)


def from_lines(lines: List[str]) -> RopeEngine:
    """Create rope from lines."""
    return RopeEngine('\n'.join(lines))


def concat_ropes(*ropes: RopeEngine) -> RopeEngine:
    """Concatenate multiple ropes."""
    if not ropes:
        return RopeEngine()

    result = ropes[0]
    for rope in ropes[1:]:
        result = result.concat(rope)

    return result
