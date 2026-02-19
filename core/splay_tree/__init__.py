"""
BAEL Splay Tree Engine Implementation
=====================================

Self-adjusting binary search tree.

"Ba'el brings important nodes to the surface." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, Generic, Iterator, List, Optional, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.SplayTree")

K = TypeVar('K')
V = TypeVar('V')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SplayNode(Generic[K, V]):
    """Node in splay tree."""
    key: K
    value: V
    left: Optional['SplayNode[K, V]'] = None
    right: Optional['SplayNode[K, V]'] = None
    parent: Optional['SplayNode[K, V]'] = None
    size: int = 1  # Subtree size for order statistics


@dataclass
class SplayTreeStats:
    """Splay tree statistics."""
    size: int = 0
    splays: int = 0
    rotations: int = 0


# ============================================================================
# SPLAY TREE ENGINE
# ============================================================================

class SplayTreeEngine(Generic[K, V]):
    """
    Splay Tree - self-adjusting BST.

    Features:
    - O(log n) amortized operations
    - Recently accessed elements near root
    - Good for temporal locality
    - Split and merge operations

    "Ba'el prioritizes the frequently accessed." — Ba'el
    """

    def __init__(self):
        """Initialize splay tree."""
        self._root: Optional[SplayNode[K, V]] = None
        self._stats = SplayTreeStats()
        self._lock = threading.RLock()

        logger.debug("Splay tree initialized")

    def _update_size(self, node: Optional[SplayNode[K, V]]) -> None:
        """Update subtree size."""
        if node:
            left_size = node.left.size if node.left else 0
            right_size = node.right.size if node.right else 0
            node.size = 1 + left_size + right_size

    # ========================================================================
    # ROTATIONS
    # ========================================================================

    def _rotate_left(self, x: SplayNode[K, V]) -> None:
        """Left rotation."""
        y = x.right
        if not y:
            return

        x.right = y.left
        if y.left:
            y.left.parent = x

        y.parent = x.parent

        if not x.parent:
            self._root = y
        elif x == x.parent.left:
            x.parent.left = y
        else:
            x.parent.right = y

        y.left = x
        x.parent = y

        self._update_size(x)
        self._update_size(y)
        self._stats.rotations += 1

    def _rotate_right(self, x: SplayNode[K, V]) -> None:
        """Right rotation."""
        y = x.left
        if not y:
            return

        x.left = y.right
        if y.right:
            y.right.parent = x

        y.parent = x.parent

        if not x.parent:
            self._root = y
        elif x == x.parent.right:
            x.parent.right = y
        else:
            x.parent.left = y

        y.right = x
        x.parent = y

        self._update_size(x)
        self._update_size(y)
        self._stats.rotations += 1

    # ========================================================================
    # SPLAY OPERATION
    # ========================================================================

    def _splay(self, x: SplayNode[K, V]) -> None:
        """Splay node x to root."""
        self._stats.splays += 1

        while x.parent:
            if not x.parent.parent:
                # Zig step
                if x == x.parent.left:
                    self._rotate_right(x.parent)
                else:
                    self._rotate_left(x.parent)
            elif x == x.parent.left and x.parent == x.parent.parent.left:
                # Zig-zig step (left-left)
                self._rotate_right(x.parent.parent)
                self._rotate_right(x.parent)
            elif x == x.parent.right and x.parent == x.parent.parent.right:
                # Zig-zig step (right-right)
                self._rotate_left(x.parent.parent)
                self._rotate_left(x.parent)
            elif x == x.parent.right and x.parent == x.parent.parent.left:
                # Zig-zag step (left-right)
                self._rotate_left(x.parent)
                self._rotate_right(x.parent)
            else:
                # Zig-zag step (right-left)
                self._rotate_right(x.parent)
                self._rotate_left(x.parent)

    # ========================================================================
    # BASIC OPERATIONS
    # ========================================================================

    def insert(self, key: K, value: V) -> None:
        """
        Insert key-value pair.

        Args:
            key: Key to insert
            value: Value to store
        """
        with self._lock:
            new_node = SplayNode(key=key, value=value)

            if not self._root:
                self._root = new_node
                self._stats.size = 1
                return

            # BST insert
            current = self._root
            parent = None

            while current:
                parent = current
                current.size += 1

                if key < current.key:
                    current = current.left
                elif key > current.key:
                    current = current.right
                else:
                    # Key exists, update value
                    current.value = value
                    self._splay(current)
                    return

            new_node.parent = parent

            if key < parent.key:
                parent.left = new_node
            else:
                parent.right = new_node

            self._stats.size += 1
            self._splay(new_node)

    def get(self, key: K) -> Optional[V]:
        """
        Get value for key.

        Args:
            key: Key to find

        Returns:
            Value or None
        """
        with self._lock:
            node = self._find(key)

            if node:
                self._splay(node)
                return node.value

            return None

    def _find(self, key: K) -> Optional[SplayNode[K, V]]:
        """Find node with key."""
        current = self._root

        while current:
            if key < current.key:
                current = current.left
            elif key > current.key:
                current = current.right
            else:
                return current

        return None

    def delete(self, key: K) -> bool:
        """
        Delete key from tree.

        Args:
            key: Key to delete

        Returns:
            True if deleted
        """
        with self._lock:
            node = self._find(key)

            if not node:
                return False

            self._splay(node)

            if not node.left:
                self._root = node.right
                if self._root:
                    self._root.parent = None
            elif not node.right:
                self._root = node.left
                if self._root:
                    self._root.parent = None
            else:
                # Find maximum in left subtree
                left_tree = node.left
                left_tree.parent = None

                right_tree = node.right
                right_tree.parent = None

                # Splay maximum in left tree to root
                max_node = left_tree
                while max_node.right:
                    max_node = max_node.right

                # Temporarily set as root to splay
                temp_root = self._root
                self._root = left_tree
                self._splay(max_node)

                # Now max_node is root of left tree and has no right child
                max_node.right = right_tree
                right_tree.parent = max_node

                self._root = max_node
                self._update_size(self._root)

            self._stats.size -= 1
            return True

    def contains(self, key: K) -> bool:
        """Check if key exists."""
        return self.get(key) is not None

    # ========================================================================
    # ORDER STATISTICS
    # ========================================================================

    def kth_element(self, k: int) -> Optional[Tuple[K, V]]:
        """
        Get k-th smallest element (1-indexed).

        Args:
            k: Position (1-indexed)

        Returns:
            (key, value) tuple or None
        """
        with self._lock:
            if not self._root or k < 1 or k > self._stats.size:
                return None

            node = self._kth_node(k)

            if node:
                self._splay(node)
                return (node.key, node.value)

            return None

    def _kth_node(self, k: int) -> Optional[SplayNode[K, V]]:
        """Find k-th node."""
        current = self._root

        while current:
            left_size = current.left.size if current.left else 0

            if k == left_size + 1:
                return current
            elif k <= left_size:
                current = current.left
            else:
                k -= left_size + 1
                current = current.right

        return None

    def rank(self, key: K) -> int:
        """
        Get rank of key (1-indexed).

        Args:
            key: Key to find

        Returns:
            Rank (0 if not found)
        """
        with self._lock:
            r = 0
            current = self._root

            while current:
                left_size = current.left.size if current.left else 0

                if key < current.key:
                    current = current.left
                elif key > current.key:
                    r += left_size + 1
                    current = current.right
                else:
                    return r + left_size + 1

            return 0

    # ========================================================================
    # SPLIT AND MERGE
    # ========================================================================

    def split(self, key: K) -> Tuple['SplayTreeEngine[K, V]', 'SplayTreeEngine[K, V]']:
        """
        Split tree at key.

        Args:
            key: Split key

        Returns:
            (left_tree, right_tree) where left < key <= right
        """
        with self._lock:
            left = SplayTreeEngine[K, V]()
            right = SplayTreeEngine[K, V]()

            if not self._root:
                return left, right

            # Find split point
            node = self._find(key)

            if node:
                self._splay(node)

                # Split: left subtree is left tree
                left._root = self._root.left
                if left._root:
                    left._root.parent = None
                    left._stats.size = left._root.size

                # Root and right subtree is right tree
                right._root = self._root
                right._root.left = None
                self._update_size(right._root)
                right._stats.size = right._root.size
            else:
                # Find largest key < given key
                current = self._root
                split_node = None

                while current:
                    if key <= current.key:
                        current = current.left
                    else:
                        split_node = current
                        current = current.right

                if split_node:
                    self._splay(split_node)

                    right._root = split_node.right
                    if right._root:
                        right._root.parent = None
                        right._stats.size = right._root.size

                    left._root = split_node
                    left._root.right = None
                    self._update_size(left._root)
                    left._stats.size = left._root.size
                else:
                    right._root = self._root
                    right._stats.size = self._stats.size

            self._root = None
            self._stats.size = 0

            return left, right

    def merge(self, other: 'SplayTreeEngine[K, V]') -> None:
        """
        Merge other tree into this (all keys in other must be > all keys in self).

        Args:
            other: Tree to merge
        """
        with self._lock:
            with other._lock:
                if not self._root:
                    self._root = other._root
                    self._stats.size = other._stats.size
                    other._root = None
                    other._stats.size = 0
                    return

                if not other._root:
                    return

                # Splay maximum in self
                max_node = self._root
                while max_node.right:
                    max_node = max_node.right

                self._splay(max_node)

                # Attach other as right child
                self._root.right = other._root
                other._root.parent = self._root

                self._update_size(self._root)
                self._stats.size += other._stats.size

                other._root = None
                other._stats.size = 0

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def min_key(self) -> Optional[K]:
        """Get minimum key."""
        with self._lock:
            if not self._root:
                return None

            node = self._root
            while node.left:
                node = node.left

            self._splay(node)
            return node.key

    def max_key(self) -> Optional[K]:
        """Get maximum key."""
        with self._lock:
            if not self._root:
                return None

            node = self._root
            while node.right:
                node = node.right

            self._splay(node)
            return node.key

    def __len__(self) -> int:
        return self._stats.size

    def __contains__(self, key: K) -> bool:
        return self.contains(key)

    def __iter__(self) -> Iterator[Tuple[K, V]]:
        """In-order iteration."""
        def inorder(node: Optional[SplayNode[K, V]]) -> Iterator[Tuple[K, V]]:
            if node:
                yield from inorder(node.left)
                yield (node.key, node.value)
                yield from inorder(node.right)

        return inorder(self._root)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'size': self._stats.size,
            'splays': self._stats.splays,
            'rotations': self._stats.rotations
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_splay_tree() -> SplayTreeEngine:
    """Create empty splay tree."""
    return SplayTreeEngine()


def from_dict(data: Dict[K, V]) -> SplayTreeEngine[K, V]:
    """Create splay tree from dictionary."""
    tree = SplayTreeEngine[K, V]()

    for key, value in data.items():
        tree.insert(key, value)

    return tree


def from_pairs(pairs: List[Tuple[K, V]]) -> SplayTreeEngine[K, V]:
    """Create splay tree from key-value pairs."""
    tree = SplayTreeEngine[K, V]()

    for key, value in pairs:
        tree.insert(key, value)

    return tree
