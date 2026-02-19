"""
BAEL AVL Tree Engine Implementation
===================================

Height-balanced binary search tree.

"Ba'el maintains equilibrium across all dimensions." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, Generic, Iterator, List, Optional, Tuple, TypeVar
from dataclasses import dataclass, field

logger = logging.getLogger("BAEL.AVLTree")

K = TypeVar('K')
V = TypeVar('V')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class AVLNode(Generic[K, V]):
    """Node in AVL tree."""
    key: K
    value: V
    height: int = 1
    left: Optional['AVLNode[K, V]'] = None
    right: Optional['AVLNode[K, V]'] = None
    size: int = 1  # Subtree size


@dataclass
class AVLTreeStats:
    """AVL tree statistics."""
    size: int = 0
    rotations: int = 0
    height: int = 0


# ============================================================================
# AVL TREE ENGINE
# ============================================================================

class AVLTreeEngine(Generic[K, V]):
    """
    AVL Tree - height-balanced BST.

    Properties:
    - Height of left and right subtrees differ by at most 1
    - O(log n) guaranteed for all operations
    - Stricter balance than Red-Black tree

    "Ba'el enforces perfect height balance." — Ba'el
    """

    def __init__(self):
        """Initialize AVL tree."""
        self._root: Optional[AVLNode[K, V]] = None
        self._stats = AVLTreeStats()
        self._lock = threading.RLock()

        logger.debug("AVL tree initialized")

    def _height(self, node: Optional[AVLNode[K, V]]) -> int:
        """Get node height."""
        return node.height if node else 0

    def _size(self, node: Optional[AVLNode[K, V]]) -> int:
        """Get subtree size."""
        return node.size if node else 0

    def _update(self, node: AVLNode[K, V]) -> None:
        """Update node height and size."""
        node.height = 1 + max(self._height(node.left), self._height(node.right))
        node.size = 1 + self._size(node.left) + self._size(node.right)

    def _balance_factor(self, node: Optional[AVLNode[K, V]]) -> int:
        """Get balance factor (left_height - right_height)."""
        if not node:
            return 0
        return self._height(node.left) - self._height(node.right)

    # ========================================================================
    # ROTATIONS
    # ========================================================================

    def _rotate_right(self, y: AVLNode[K, V]) -> AVLNode[K, V]:
        """Right rotation."""
        x = y.left
        T2 = x.right

        x.right = y
        y.left = T2

        self._update(y)
        self._update(x)

        self._stats.rotations += 1
        return x

    def _rotate_left(self, x: AVLNode[K, V]) -> AVLNode[K, V]:
        """Left rotation."""
        y = x.right
        T2 = y.left

        y.left = x
        x.right = T2

        self._update(x)
        self._update(y)

        self._stats.rotations += 1
        return y

    def _rebalance(self, node: AVLNode[K, V]) -> AVLNode[K, V]:
        """Rebalance node if needed."""
        self._update(node)
        balance = self._balance_factor(node)

        # Left heavy
        if balance > 1:
            if self._balance_factor(node.left) < 0:
                # Left-Right case
                node.left = self._rotate_left(node.left)
            # Left-Left case
            return self._rotate_right(node)

        # Right heavy
        if balance < -1:
            if self._balance_factor(node.right) > 0:
                # Right-Left case
                node.right = self._rotate_right(node.right)
            # Right-Right case
            return self._rotate_left(node)

        return node

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
            self._root = self._insert(self._root, key, value)
            self._stats.height = self._height(self._root)

    def _insert(
        self,
        node: Optional[AVLNode[K, V]],
        key: K,
        value: V
    ) -> AVLNode[K, V]:
        """Insert recursively."""
        if not node:
            self._stats.size += 1
            return AVLNode(key=key, value=value)

        if key < node.key:
            node.left = self._insert(node.left, key, value)
        elif key > node.key:
            node.right = self._insert(node.right, key, value)
        else:
            node.value = value
            return node

        return self._rebalance(node)

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
            if not self.contains(key):
                return False

            self._root = self._delete(self._root, key)
            self._stats.size -= 1
            self._stats.height = self._height(self._root)
            return True

    def _delete(
        self,
        node: Optional[AVLNode[K, V]],
        key: K
    ) -> Optional[AVLNode[K, V]]:
        """Delete recursively."""
        if not node:
            return None

        if key < node.key:
            node.left = self._delete(node.left, key)
        elif key > node.key:
            node.right = self._delete(node.right, key)
        else:
            # Node to delete found
            if not node.left:
                return node.right
            elif not node.right:
                return node.left
            else:
                # Node has two children
                # Find inorder successor
                successor = self._minimum(node.right)
                node.key = successor.key
                node.value = successor.value
                node.right = self._delete(node.right, successor.key)

        return self._rebalance(node)

    def _minimum(self, node: AVLNode[K, V]) -> AVLNode[K, V]:
        """Find minimum in subtree."""
        while node.left:
            node = node.left
        return node

    def _maximum(self, node: AVLNode[K, V]) -> AVLNode[K, V]:
        """Find maximum in subtree."""
        while node.right:
            node = node.right
        return node

    # ========================================================================
    # SEARCH
    # ========================================================================

    def get(self, key: K) -> Optional[V]:
        """Get value for key."""
        with self._lock:
            node = self._find(self._root, key)
            return node.value if node else None

    def _find(
        self,
        node: Optional[AVLNode[K, V]],
        key: K
    ) -> Optional[AVLNode[K, V]]:
        """Find node with key."""
        if not node:
            return None

        if key < node.key:
            return self._find(node.left, key)
        elif key > node.key:
            return self._find(node.right, key)
        else:
            return node

    def contains(self, key: K) -> bool:
        """Check if key exists."""
        return self._find(self._root, key) is not None

    # ========================================================================
    # RANGE QUERIES
    # ========================================================================

    def range(self, lo: K, hi: K) -> List[Tuple[K, V]]:
        """
        Get all keys in range [lo, hi].

        Args:
            lo: Low key (inclusive)
            hi: High key (inclusive)

        Returns:
            List of (key, value) pairs
        """
        with self._lock:
            result = []
            self._range(self._root, lo, hi, result)
            return result

    def _range(
        self,
        node: Optional[AVLNode[K, V]],
        lo: K,
        hi: K,
        result: List[Tuple[K, V]]
    ) -> None:
        """Range query recursively."""
        if not node:
            return

        if lo < node.key:
            self._range(node.left, lo, hi, result)

        if lo <= node.key <= hi:
            result.append((node.key, node.value))

        if hi > node.key:
            self._range(node.right, lo, hi, result)

    # ========================================================================
    # ORDER STATISTICS
    # ========================================================================

    def min_key(self) -> Optional[K]:
        """Get minimum key."""
        with self._lock:
            if not self._root:
                return None
            return self._minimum(self._root).key

    def max_key(self) -> Optional[K]:
        """Get maximum key."""
        with self._lock:
            if not self._root:
                return None
            return self._maximum(self._root).key

    def kth_element(self, k: int) -> Optional[Tuple[K, V]]:
        """Get k-th smallest element (1-indexed)."""
        with self._lock:
            if k < 1 or k > self._stats.size:
                return None

            node = self._kth_node(self._root, k)
            return (node.key, node.value) if node else None

    def _kth_node(
        self,
        node: Optional[AVLNode[K, V]],
        k: int
    ) -> Optional[AVLNode[K, V]]:
        """Find k-th node."""
        if not node:
            return None

        left_size = self._size(node.left)

        if k == left_size + 1:
            return node
        elif k <= left_size:
            return self._kth_node(node.left, k)
        else:
            return self._kth_node(node.right, k - left_size - 1)

    def rank(self, key: K) -> int:
        """Get rank of key (1-indexed), 0 if not found."""
        with self._lock:
            return self._rank(self._root, key)

    def _rank(self, node: Optional[AVLNode[K, V]], key: K) -> int:
        """Get rank recursively."""
        if not node:
            return 0

        left_size = self._size(node.left)

        if key < node.key:
            return self._rank(node.left, key)
        elif key > node.key:
            result = self._rank(node.right, key)
            return (left_size + 1 + result) if result > 0 else 0
        else:
            return left_size + 1

    def floor(self, key: K) -> Optional[K]:
        """Find largest key <= given key."""
        with self._lock:
            node = self._floor(self._root, key)
            return node.key if node else None

    def _floor(
        self,
        node: Optional[AVLNode[K, V]],
        key: K
    ) -> Optional[AVLNode[K, V]]:
        """Find floor recursively."""
        if not node:
            return None

        if key == node.key:
            return node

        if key < node.key:
            return self._floor(node.left, key)

        right_floor = self._floor(node.right, key)
        return right_floor if right_floor else node

    def ceiling(self, key: K) -> Optional[K]:
        """Find smallest key >= given key."""
        with self._lock:
            node = self._ceiling(self._root, key)
            return node.key if node else None

    def _ceiling(
        self,
        node: Optional[AVLNode[K, V]],
        key: K
    ) -> Optional[AVLNode[K, V]]:
        """Find ceiling recursively."""
        if not node:
            return None

        if key == node.key:
            return node

        if key > node.key:
            return self._ceiling(node.right, key)

        left_ceiling = self._ceiling(node.left, key)
        return left_ceiling if left_ceiling else node

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def __len__(self) -> int:
        return self._stats.size

    def __contains__(self, key: K) -> bool:
        return self.contains(key)

    def __iter__(self) -> Iterator[Tuple[K, V]]:
        """In-order iteration."""
        def inorder(node: Optional[AVLNode[K, V]]) -> Iterator[Tuple[K, V]]:
            if node:
                yield from inorder(node.left)
                yield (node.key, node.value)
                yield from inorder(node.right)

        return inorder(self._root)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        with self._lock:
            return {
                'size': self._stats.size,
                'height': self._stats.height,
                'rotations': self._stats.rotations
            }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_avl_tree() -> AVLTreeEngine:
    """Create empty AVL tree."""
    return AVLTreeEngine()


def from_dict(data: Dict[K, V]) -> AVLTreeEngine[K, V]:
    """Create AVL tree from dictionary."""
    tree = AVLTreeEngine[K, V]()
    for key, value in data.items():
        tree.insert(key, value)
    return tree


def from_pairs(pairs: List[Tuple[K, V]]) -> AVLTreeEngine[K, V]:
    """Create AVL tree from pairs."""
    tree = AVLTreeEngine[K, V]()
    for key, value in pairs:
        tree.insert(key, value)
    return tree
