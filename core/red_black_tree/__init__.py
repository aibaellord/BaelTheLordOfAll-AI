"""
BAEL Red-Black Tree Engine
==========================

Self-balancing binary search tree with guaranteed O(log n) operations.

"Ba'el balances in color." — Ba'el
"""

import logging
import threading
from typing import Any, Callable, Generic, Iterator, List, Optional, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger("BAEL.RedBlackTree")


K = TypeVar('K')
V = TypeVar('V')


# ============================================================================
# COLOR
# ============================================================================

class Color(Enum):
    RED = 0
    BLACK = 1


# ============================================================================
# RED-BLACK TREE NODE
# ============================================================================

class RBNode(Generic[K, V]):
    """Node in red-black tree."""

    __slots__ = ['key', 'value', 'color', 'left', 'right', 'parent']

    def __init__(self, key: K, value: V, color: Color = Color.RED):
        self.key = key
        self.value = value
        self.color = color
        self.left: Optional['RBNode[K, V]'] = None
        self.right: Optional['RBNode[K, V]'] = None
        self.parent: Optional['RBNode[K, V]'] = None

    @property
    def is_red(self) -> bool:
        return self.color == Color.RED

    @property
    def is_black(self) -> bool:
        return self.color == Color.BLACK


# ============================================================================
# RED-BLACK TREE
# ============================================================================

class RedBlackTree(Generic[K, V]):
    """
    Red-Black Tree: self-balancing BST.

    Properties:
    1. Every node is red or black
    2. Root is black
    3. Every leaf (NIL) is black
    4. Red node has black children
    5. All paths from node to descendant leaves have same black count

    Features:
    - O(log n) insert, delete, search
    - Guaranteed balance

    "Ba'el colors for balance." — Ba'el
    """

    def __init__(self, comparator: Optional[Callable[[K, K], int]] = None):
        """
        Initialize red-black tree.

        Args:
            comparator: Optional comparison function
        """
        self._root: Optional[RBNode[K, V]] = None
        self._size = 0
        self._comparator = comparator
        self._lock = threading.RLock()

    def _compare(self, a: K, b: K) -> int:
        """Compare two keys."""
        if self._comparator:
            return self._comparator(a, b)

        if a < b:
            return -1
        if a > b:
            return 1
        return 0

    def _is_red(self, node: Optional[RBNode[K, V]]) -> bool:
        """Check if node is red (NIL is black)."""
        return node is not None and node.is_red

    def _rotate_left(self, x: RBNode[K, V]):
        """Left rotation around x."""
        y = x.right
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

    def _rotate_right(self, x: RBNode[K, V]):
        """Right rotation around x."""
        y = x.left
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

    def insert(self, key: K, value: V):
        """
        Insert key-value pair.

        O(log n).
        """
        with self._lock:
            new_node = RBNode(key, value, Color.RED)

            if not self._root:
                self._root = new_node
                self._root.color = Color.BLACK
                self._size = 1
                return

            # BST insert
            current = self._root
            parent = None

            while current:
                parent = current
                cmp = self._compare(key, current.key)

                if cmp < 0:
                    current = current.left
                elif cmp > 0:
                    current = current.right
                else:
                    # Key exists, update value
                    current.value = value
                    return

            new_node.parent = parent

            if self._compare(key, parent.key) < 0:
                parent.left = new_node
            else:
                parent.right = new_node

            self._size += 1

            # Fix violations
            self._insert_fixup(new_node)

    def _insert_fixup(self, z: RBNode[K, V]):
        """Fix red-black properties after insertion."""
        while z.parent and z.parent.is_red:
            if z.parent == z.parent.parent.left:
                y = z.parent.parent.right  # Uncle

                if self._is_red(y):
                    # Case 1: Uncle is red
                    z.parent.color = Color.BLACK
                    y.color = Color.BLACK
                    z.parent.parent.color = Color.RED
                    z = z.parent.parent
                else:
                    if z == z.parent.right:
                        # Case 2: Uncle is black, z is right child
                        z = z.parent
                        self._rotate_left(z)

                    # Case 3: Uncle is black, z is left child
                    z.parent.color = Color.BLACK
                    z.parent.parent.color = Color.RED
                    self._rotate_right(z.parent.parent)
            else:
                y = z.parent.parent.left  # Uncle

                if self._is_red(y):
                    z.parent.color = Color.BLACK
                    y.color = Color.BLACK
                    z.parent.parent.color = Color.RED
                    z = z.parent.parent
                else:
                    if z == z.parent.left:
                        z = z.parent
                        self._rotate_right(z)

                    z.parent.color = Color.BLACK
                    z.parent.parent.color = Color.RED
                    self._rotate_left(z.parent.parent)

            if not z.parent:
                break

        self._root.color = Color.BLACK

    def delete(self, key: K) -> bool:
        """
        Delete key.

        O(log n). Returns True if key was found.
        """
        with self._lock:
            node = self._find_node(key)

            if not node:
                return False

            self._delete_node(node)
            self._size -= 1
            return True

    def _find_node(self, key: K) -> Optional[RBNode[K, V]]:
        """Find node with key."""
        current = self._root

        while current:
            cmp = self._compare(key, current.key)

            if cmp < 0:
                current = current.left
            elif cmp > 0:
                current = current.right
            else:
                return current

        return None

    def _delete_node(self, z: RBNode[K, V]):
        """Delete node z."""
        y = z
        y_original_color = y.color

        if not z.left:
            x = z.right
            x_parent = z.parent
            self._transplant(z, z.right)
        elif not z.right:
            x = z.left
            x_parent = z.parent
            self._transplant(z, z.left)
        else:
            y = self._minimum(z.right)
            y_original_color = y.color
            x = y.right

            if y.parent == z:
                x_parent = y
            else:
                x_parent = y.parent
                self._transplant(y, y.right)
                y.right = z.right
                y.right.parent = y

            self._transplant(z, y)
            y.left = z.left
            y.left.parent = y
            y.color = z.color

        if y_original_color == Color.BLACK:
            self._delete_fixup(x, x_parent)

    def _transplant(self, u: RBNode[K, V], v: Optional[RBNode[K, V]]):
        """Replace subtree rooted at u with subtree rooted at v."""
        if not u.parent:
            self._root = v
        elif u == u.parent.left:
            u.parent.left = v
        else:
            u.parent.right = v

        if v:
            v.parent = u.parent

    def _minimum(self, node: RBNode[K, V]) -> RBNode[K, V]:
        """Find minimum node in subtree."""
        while node.left:
            node = node.left
        return node

    def _delete_fixup(self, x: Optional[RBNode[K, V]], x_parent: Optional[RBNode[K, V]]):
        """Fix red-black properties after deletion."""
        while x != self._root and not self._is_red(x):
            if x_parent is None:
                break

            if x == x_parent.left:
                w = x_parent.right

                if w and self._is_red(w):
                    w.color = Color.BLACK
                    x_parent.color = Color.RED
                    self._rotate_left(x_parent)
                    w = x_parent.right

                if w and not self._is_red(w.left) and not self._is_red(w.right):
                    w.color = Color.RED
                    x = x_parent
                    x_parent = x.parent if x else None
                else:
                    if w and not self._is_red(w.right):
                        if w.left:
                            w.left.color = Color.BLACK
                        w.color = Color.RED
                        self._rotate_right(w)
                        w = x_parent.right

                    if w:
                        w.color = x_parent.color
                    x_parent.color = Color.BLACK
                    if w and w.right:
                        w.right.color = Color.BLACK
                    self._rotate_left(x_parent)
                    x = self._root
                    break
            else:
                w = x_parent.left

                if w and self._is_red(w):
                    w.color = Color.BLACK
                    x_parent.color = Color.RED
                    self._rotate_right(x_parent)
                    w = x_parent.left

                if w and not self._is_red(w.right) and not self._is_red(w.left):
                    w.color = Color.RED
                    x = x_parent
                    x_parent = x.parent if x else None
                else:
                    if w and not self._is_red(w.left):
                        if w.right:
                            w.right.color = Color.BLACK
                        w.color = Color.RED
                        self._rotate_left(w)
                        w = x_parent.left

                    if w:
                        w.color = x_parent.color
                    x_parent.color = Color.BLACK
                    if w and w.left:
                        w.left.color = Color.BLACK
                    self._rotate_right(x_parent)
                    x = self._root
                    break

        if x:
            x.color = Color.BLACK

    def get(self, key: K) -> Optional[V]:
        """Get value for key."""
        with self._lock:
            node = self._find_node(key)
            return node.value if node else None

    def contains(self, key: K) -> bool:
        """Check if key exists."""
        return self._find_node(key) is not None

    def __getitem__(self, key: K) -> V:
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key: K, value: V):
        self.insert(key, value)

    def __delitem__(self, key: K):
        if not self.delete(key):
            raise KeyError(key)

    def __contains__(self, key: K) -> bool:
        return self.contains(key)

    def __len__(self) -> int:
        return self._size

    def min(self) -> Optional[Tuple[K, V]]:
        """Get minimum key-value pair."""
        with self._lock:
            if not self._root:
                return None
            node = self._minimum(self._root)
            return (node.key, node.value)

    def max(self) -> Optional[Tuple[K, V]]:
        """Get maximum key-value pair."""
        with self._lock:
            if not self._root:
                return None
            node = self._root
            while node.right:
                node = node.right
            return (node.key, node.value)

    def items(self) -> List[Tuple[K, V]]:
        """Get all key-value pairs in order."""
        with self._lock:
            result = []
            self._inorder(self._root, result)
            return result

    def _inorder(self, node: Optional[RBNode[K, V]], result: List):
        if node:
            self._inorder(node.left, result)
            result.append((node.key, node.value))
            self._inorder(node.right, result)

    def keys(self) -> List[K]:
        """Get all keys in order."""
        return [k for k, v in self.items()]

    def values(self) -> List[V]:
        """Get all values in key order."""
        return [v for k, v in self.items()]

    def __iter__(self) -> Iterator[K]:
        return iter(self.keys())


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_red_black_tree() -> RedBlackTree:
    """Create empty red-black tree."""
    return RedBlackTree()


def rb_tree_from_pairs(pairs: List[Tuple[Any, Any]]) -> RedBlackTree:
    """Create red-black tree from key-value pairs."""
    tree = RedBlackTree()
    for k, v in pairs:
        tree.insert(k, v)
    return tree
