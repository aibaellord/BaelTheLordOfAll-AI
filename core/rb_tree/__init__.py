"""
BAEL Red-Black Tree Engine Implementation
==========================================

Self-balancing BST with O(log n) operations.

"Ba'el maintains perfect balance between dark and light." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, Generic, Iterator, List, Optional, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.RedBlackTree")

K = TypeVar('K')
V = TypeVar('V')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class Color(Enum):
    """Node color."""
    RED = "red"
    BLACK = "black"


@dataclass
class RBNode(Generic[K, V]):
    """Node in Red-Black tree."""
    key: K
    value: V
    color: Color = Color.RED
    left: Optional['RBNode[K, V]'] = None
    right: Optional['RBNode[K, V]'] = None
    parent: Optional['RBNode[K, V]'] = None
    size: int = 1  # Subtree size for order statistics


@dataclass
class RedBlackTreeStats:
    """Red-Black tree statistics."""
    size: int = 0
    rotations: int = 0
    recolorings: int = 0
    black_height: int = 0


# ============================================================================
# RED-BLACK TREE ENGINE
# ============================================================================

class RedBlackTreeEngine(Generic[K, V]):
    """
    Red-Black Tree - self-balancing BST.

    Properties:
    1. Every node is red or black
    2. Root is black
    3. All leaves (NIL) are black
    4. Red node has black children
    5. All paths have same black height

    "Ba'el enforces the laws of chromatic balance." — Ba'el
    """

    def __init__(self):
        """Initialize Red-Black tree."""
        self._NIL: RBNode[K, V] = RBNode(key=None, value=None, color=Color.BLACK)
        self._root: RBNode[K, V] = self._NIL
        self._stats = RedBlackTreeStats()
        self._lock = threading.RLock()

        logger.debug("Red-Black tree initialized")

    def _is_nil(self, node: RBNode[K, V]) -> bool:
        """Check if node is NIL."""
        return node is self._NIL or node is None

    def _update_size(self, node: RBNode[K, V]) -> None:
        """Update subtree size."""
        if not self._is_nil(node):
            left_size = node.left.size if not self._is_nil(node.left) else 0
            right_size = node.right.size if not self._is_nil(node.right) else 0
            node.size = 1 + left_size + right_size

    # ========================================================================
    # ROTATIONS
    # ========================================================================

    def _rotate_left(self, x: RBNode[K, V]) -> None:
        """Left rotation."""
        y = x.right
        x.right = y.left

        if not self._is_nil(y.left):
            y.left.parent = x

        y.parent = x.parent

        if self._is_nil(x.parent):
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

    def _rotate_right(self, x: RBNode[K, V]) -> None:
        """Right rotation."""
        y = x.left
        x.left = y.right

        if not self._is_nil(y.right):
            y.right.parent = x

        y.parent = x.parent

        if self._is_nil(x.parent):
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
    # INSERT
    # ========================================================================

    def insert(self, key: K, value: V) -> None:
        """
        Insert key-value pair.

        Args:
            key: Key to insert
            value: Value to store
        """
        with self._lock:
            new_node = RBNode(key=key, value=value, color=Color.RED)
            new_node.left = self._NIL
            new_node.right = self._NIL

            parent = None
            current = self._root

            while not self._is_nil(current):
                parent = current

                if key < current.key:
                    current = current.left
                elif key > current.key:
                    current = current.right
                else:
                    # Key exists, update value
                    current.value = value
                    return

            new_node.parent = parent

            if parent is None:
                self._root = new_node
            elif key < parent.key:
                parent.left = new_node
            else:
                parent.right = new_node

            # Update sizes up the tree
            node = new_node.parent
            while node:
                self._update_size(node)
                node = node.parent

            self._stats.size += 1
            self._insert_fixup(new_node)

    def _insert_fixup(self, z: RBNode[K, V]) -> None:
        """Fix Red-Black properties after insert."""
        while z.parent and z.parent.color == Color.RED:
            if z.parent == z.parent.parent.left:
                y = z.parent.parent.right

                if y.color == Color.RED:
                    # Case 1: Uncle is red
                    z.parent.color = Color.BLACK
                    y.color = Color.BLACK
                    z.parent.parent.color = Color.RED
                    z = z.parent.parent
                    self._stats.recolorings += 3
                else:
                    if z == z.parent.right:
                        # Case 2: Uncle is black, z is right child
                        z = z.parent
                        self._rotate_left(z)

                    # Case 3: Uncle is black, z is left child
                    z.parent.color = Color.BLACK
                    z.parent.parent.color = Color.RED
                    self._rotate_right(z.parent.parent)
                    self._stats.recolorings += 2
            else:
                # Mirror cases
                y = z.parent.parent.left

                if y.color == Color.RED:
                    z.parent.color = Color.BLACK
                    y.color = Color.BLACK
                    z.parent.parent.color = Color.RED
                    z = z.parent.parent
                    self._stats.recolorings += 3
                else:
                    if z == z.parent.left:
                        z = z.parent
                        self._rotate_right(z)

                    z.parent.color = Color.BLACK
                    z.parent.parent.color = Color.RED
                    self._rotate_left(z.parent.parent)
                    self._stats.recolorings += 2

        self._root.color = Color.BLACK

    # ========================================================================
    # DELETE
    # ========================================================================

    def delete(self, key: K) -> bool:
        """
        Delete key from tree.

        Args:
            key: Key to delete

        Returns:
            True if deleted
        """
        with self._lock:
            z = self._find_node(key)

            if self._is_nil(z):
                return False

            y = z
            y_original_color = y.color

            if self._is_nil(z.left):
                x = z.right
                self._transplant(z, z.right)
            elif self._is_nil(z.right):
                x = z.left
                self._transplant(z, z.left)
            else:
                y = self._minimum(z.right)
                y_original_color = y.color
                x = y.right

                if y.parent == z:
                    x.parent = y
                else:
                    self._transplant(y, y.right)
                    y.right = z.right
                    y.right.parent = y

                self._transplant(z, y)
                y.left = z.left
                y.left.parent = y
                y.color = z.color

            # Update sizes
            node = x.parent
            while node:
                self._update_size(node)
                node = node.parent

            self._stats.size -= 1

            if y_original_color == Color.BLACK:
                self._delete_fixup(x)

            return True

    def _transplant(self, u: RBNode[K, V], v: RBNode[K, V]) -> None:
        """Replace subtree rooted at u with subtree rooted at v."""
        if self._is_nil(u.parent):
            self._root = v
        elif u == u.parent.left:
            u.parent.left = v
        else:
            u.parent.right = v

        v.parent = u.parent

    def _delete_fixup(self, x: RBNode[K, V]) -> None:
        """Fix Red-Black properties after delete."""
        while x != self._root and x.color == Color.BLACK:
            if x == x.parent.left:
                w = x.parent.right

                if w.color == Color.RED:
                    w.color = Color.BLACK
                    x.parent.color = Color.RED
                    self._rotate_left(x.parent)
                    w = x.parent.right

                if w.left.color == Color.BLACK and w.right.color == Color.BLACK:
                    w.color = Color.RED
                    x = x.parent
                else:
                    if w.right.color == Color.BLACK:
                        w.left.color = Color.BLACK
                        w.color = Color.RED
                        self._rotate_right(w)
                        w = x.parent.right

                    w.color = x.parent.color
                    x.parent.color = Color.BLACK
                    w.right.color = Color.BLACK
                    self._rotate_left(x.parent)
                    x = self._root
            else:
                # Mirror cases
                w = x.parent.left

                if w.color == Color.RED:
                    w.color = Color.BLACK
                    x.parent.color = Color.RED
                    self._rotate_right(x.parent)
                    w = x.parent.left

                if w.right.color == Color.BLACK and w.left.color == Color.BLACK:
                    w.color = Color.RED
                    x = x.parent
                else:
                    if w.left.color == Color.BLACK:
                        w.right.color = Color.BLACK
                        w.color = Color.RED
                        self._rotate_left(w)
                        w = x.parent.left

                    w.color = x.parent.color
                    x.parent.color = Color.BLACK
                    w.left.color = Color.BLACK
                    self._rotate_right(x.parent)
                    x = self._root

        x.color = Color.BLACK

    # ========================================================================
    # SEARCH
    # ========================================================================

    def get(self, key: K) -> Optional[V]:
        """Get value for key."""
        with self._lock:
            node = self._find_node(key)
            return node.value if not self._is_nil(node) else None

    def _find_node(self, key: K) -> RBNode[K, V]:
        """Find node with key."""
        current = self._root

        while not self._is_nil(current):
            if key < current.key:
                current = current.left
            elif key > current.key:
                current = current.right
            else:
                return current

        return self._NIL

    def contains(self, key: K) -> bool:
        """Check if key exists."""
        return not self._is_nil(self._find_node(key))

    def _minimum(self, node: RBNode[K, V]) -> RBNode[K, V]:
        """Find minimum in subtree."""
        while not self._is_nil(node.left):
            node = node.left
        return node

    def _maximum(self, node: RBNode[K, V]) -> RBNode[K, V]:
        """Find maximum in subtree."""
        while not self._is_nil(node.right):
            node = node.right
        return node

    # ========================================================================
    # ORDER STATISTICS
    # ========================================================================

    def min_key(self) -> Optional[K]:
        """Get minimum key."""
        with self._lock:
            if self._is_nil(self._root):
                return None
            return self._minimum(self._root).key

    def max_key(self) -> Optional[K]:
        """Get maximum key."""
        with self._lock:
            if self._is_nil(self._root):
                return None
            return self._maximum(self._root).key

    def kth_element(self, k: int) -> Optional[Tuple[K, V]]:
        """Get k-th smallest element (1-indexed)."""
        with self._lock:
            if k < 1 or k > self._stats.size:
                return None

            node = self._kth_node(self._root, k)
            return (node.key, node.value) if node else None

    def _kth_node(self, node: RBNode[K, V], k: int) -> Optional[RBNode[K, V]]:
        """Find k-th node."""
        if self._is_nil(node):
            return None

        left_size = node.left.size if not self._is_nil(node.left) else 0

        if k == left_size + 1:
            return node
        elif k <= left_size:
            return self._kth_node(node.left, k)
        else:
            return self._kth_node(node.right, k - left_size - 1)

    def rank(self, key: K) -> int:
        """Get rank of key (1-indexed), 0 if not found."""
        with self._lock:
            r = 0
            current = self._root

            while not self._is_nil(current):
                left_size = current.left.size if not self._is_nil(current.left) else 0

                if key < current.key:
                    current = current.left
                elif key > current.key:
                    r += left_size + 1
                    current = current.right
                else:
                    return r + left_size + 1

            return 0

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def __len__(self) -> int:
        return self._stats.size

    def __contains__(self, key: K) -> bool:
        return self.contains(key)

    def __iter__(self) -> Iterator[Tuple[K, V]]:
        """In-order iteration."""
        def inorder(node: RBNode[K, V]) -> Iterator[Tuple[K, V]]:
            if not self._is_nil(node):
                yield from inorder(node.left)
                yield (node.key, node.value)
                yield from inorder(node.right)

        return inorder(self._root)

    def black_height(self) -> int:
        """Calculate black height."""
        with self._lock:
            height = 0
            node = self._root

            while not self._is_nil(node):
                if node.color == Color.BLACK:
                    height += 1
                node = node.left

            return height

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        with self._lock:
            return {
                'size': self._stats.size,
                'rotations': self._stats.rotations,
                'recolorings': self._stats.recolorings,
                'black_height': self.black_height()
            }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_rb_tree() -> RedBlackTreeEngine:
    """Create empty Red-Black tree."""
    return RedBlackTreeEngine()


def from_dict(data: Dict[K, V]) -> RedBlackTreeEngine[K, V]:
    """Create Red-Black tree from dictionary."""
    tree = RedBlackTreeEngine[K, V]()
    for key, value in data.items():
        tree.insert(key, value)
    return tree


def from_pairs(pairs: List[Tuple[K, V]]) -> RedBlackTreeEngine[K, V]:
    """Create Red-Black tree from pairs."""
    tree = RedBlackTreeEngine[K, V]()
    for key, value in pairs:
        tree.insert(key, value)
    return tree
