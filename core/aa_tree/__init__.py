"""
BAEL AA Tree Engine
===================

Simplified red-black tree with simpler balancing.

"Ba'el simplifies balance." — Ba'el
"""

import logging
import threading
from typing import Any, Callable, Generic, Iterator, List, Optional, Tuple, TypeVar
from dataclasses import dataclass, field

logger = logging.getLogger("BAEL.AATree")


K = TypeVar('K')
V = TypeVar('V')


# ============================================================================
# AA TREE NODE
# ============================================================================

class AANode(Generic[K, V]):
    """Node in AA tree."""

    __slots__ = ['key', 'value', 'level', 'left', 'right']

    def __init__(self, key: K, value: V):
        self.key = key
        self.value = value
        self.level = 1
        self.left: Optional['AANode[K, V]'] = None
        self.right: Optional['AANode[K, V]'] = None


# ============================================================================
# AA TREE
# ============================================================================

class AATree(Generic[K, V]):
    """
    AA Tree: simplified red-black tree.

    Features:
    - O(log n) insert, delete, search
    - Simpler than red-black trees (only 2 operations: skew, split)
    - Self-balancing

    Invariants:
    1. Level of leaf is 1
    2. Level of left child < level of parent
    3. Level of right child <= level of parent
    4. Level of right grandchild < level of grandparent
    5. Every node of level > 1 has two children

    "Ba'el balances simply." — Ba'el
    """

    def __init__(self, comparator: Optional[Callable[[K, K], int]] = None):
        """
        Initialize AA tree.

        Args:
            comparator: Optional comparison function (returns <0, 0, >0)
        """
        self._root: Optional[AANode[K, V]] = None
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

    def _skew(self, node: Optional[AANode[K, V]]) -> Optional[AANode[K, V]]:
        """
        Remove left horizontal link.

        If left child has same level, rotate right.
        """
        if node is None:
            return None

        if node.left is None:
            return node

        if node.left.level == node.level:
            # Rotate right
            left = node.left
            node.left = left.right
            left.right = node
            return left

        return node

    def _split(self, node: Optional[AANode[K, V]]) -> Optional[AANode[K, V]]:
        """
        Remove consecutive horizontal links.

        If right grandchild has same level, rotate left and increase level.
        """
        if node is None:
            return None

        if node.right is None or node.right.right is None:
            return node

        if node.level == node.right.right.level:
            # Rotate left
            right = node.right
            node.right = right.left
            right.left = node
            right.level += 1
            return right

        return node

    def insert(self, key: K, value: V):
        """
        Insert key-value pair.

        O(log n).
        """
        with self._lock:
            self._root = self._insert(self._root, key, value)

    def _insert(self, node: Optional[AANode[K, V]], key: K, value: V) -> AANode[K, V]:
        if node is None:
            self._size += 1
            return AANode(key, value)

        cmp = self._compare(key, node.key)

        if cmp < 0:
            node.left = self._insert(node.left, key, value)
        elif cmp > 0:
            node.right = self._insert(node.right, key, value)
        else:
            node.value = value  # Update existing
            return node

        # Rebalance
        node = self._skew(node)
        node = self._split(node)

        return node

    def delete(self, key: K) -> bool:
        """
        Delete key.

        O(log n). Returns True if key was found.
        """
        with self._lock:
            old_size = self._size
            self._root = self._delete(self._root, key)
            return self._size < old_size

    def _delete(self, node: Optional[AANode[K, V]], key: K) -> Optional[AANode[K, V]]:
        if node is None:
            return None

        cmp = self._compare(key, node.key)

        if cmp < 0:
            node.left = self._delete(node.left, key)
        elif cmp > 0:
            node.right = self._delete(node.right, key)
        else:
            # Found the node
            self._size -= 1

            if node.left is None and node.right is None:
                return None

            if node.left is None:
                # Find successor
                successor = self._min_node(node.right)
                node.key = successor.key
                node.value = successor.value
                node.right = self._delete(node.right, successor.key)
                self._size += 1  # Undo double-decrement
            else:
                # Find predecessor
                predecessor = self._max_node(node.left)
                node.key = predecessor.key
                node.value = predecessor.value
                node.left = self._delete(node.left, predecessor.key)
                self._size += 1  # Undo double-decrement

        # Rebalance
        node = self._decrease_level(node)
        node = self._skew(node)
        if node.right:
            node.right = self._skew(node.right)
            if node.right.right:
                node.right.right = self._skew(node.right.right)
        node = self._split(node)
        if node.right:
            node.right = self._split(node.right)

        return node

    def _decrease_level(self, node: AANode[K, V]) -> AANode[K, V]:
        """Decrease level if necessary after deletion."""
        left_level = node.left.level if node.left else 0
        right_level = node.right.level if node.right else 0

        should_be = min(left_level, right_level) + 1

        if should_be < node.level:
            node.level = should_be
            if node.right and should_be < node.right.level:
                node.right.level = should_be

        return node

    def _min_node(self, node: AANode[K, V]) -> AANode[K, V]:
        """Find minimum node in subtree."""
        while node.left:
            node = node.left
        return node

    def _max_node(self, node: AANode[K, V]) -> AANode[K, V]:
        """Find maximum node in subtree."""
        while node.right:
            node = node.right
        return node

    def get(self, key: K) -> Optional[V]:
        """
        Get value for key.

        O(log n).
        """
        with self._lock:
            node = self._root

            while node:
                cmp = self._compare(key, node.key)

                if cmp < 0:
                    node = node.left
                elif cmp > 0:
                    node = node.right
                else:
                    return node.value

            return None

    def contains(self, key: K) -> bool:
        """Check if key exists."""
        return self.get(key) is not None

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
            node = self._min_node(self._root)
            return (node.key, node.value)

    def max(self) -> Optional[Tuple[K, V]]:
        """Get maximum key-value pair."""
        with self._lock:
            if not self._root:
                return None
            node = self._max_node(self._root)
            return (node.key, node.value)

    def items(self) -> List[Tuple[K, V]]:
        """Get all key-value pairs in order."""
        with self._lock:
            result = []
            self._inorder(self._root, result)
            return result

    def _inorder(self, node: Optional[AANode[K, V]], result: List):
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

    def range(self, low: K, high: K) -> List[Tuple[K, V]]:
        """Get all pairs with low <= key <= high."""
        with self._lock:
            result = []
            self._range(self._root, low, high, result)
            return result

    def _range(
        self,
        node: Optional[AANode[K, V]],
        low: K,
        high: K,
        result: List
    ):
        if not node:
            return

        if self._compare(low, node.key) <= 0:
            self._range(node.left, low, high, result)

        if (self._compare(low, node.key) <= 0 and
            self._compare(node.key, high) <= 0):
            result.append((node.key, node.value))

        if self._compare(node.key, high) < 0:
            self._range(node.right, low, high, result)


# ============================================================================
# AA TREE SET
# ============================================================================

class AATreeSet(Generic[K]):
    """
    Set implementation using AA tree.

    O(log n) operations.

    "Ba'el sets simply." — Ba'el
    """

    def __init__(self, comparator: Optional[Callable[[K, K], int]] = None):
        """Initialize set."""
        self._tree = AATree(comparator)

    def add(self, key: K):
        """Add key to set."""
        self._tree.insert(key, None)

    def remove(self, key: K) -> bool:
        """Remove key from set."""
        return self._tree.delete(key)

    def contains(self, key: K) -> bool:
        """Check if key in set."""
        return key in self._tree

    def __contains__(self, key: K) -> bool:
        return self.contains(key)

    def __len__(self) -> int:
        return len(self._tree)

    def __iter__(self) -> Iterator[K]:
        return iter(self._tree)

    def min(self) -> Optional[K]:
        """Get minimum key."""
        result = self._tree.min()
        return result[0] if result else None

    def max(self) -> Optional[K]:
        """Get maximum key."""
        result = self._tree.max()
        return result[0] if result else None

    def range(self, low: K, high: K) -> List[K]:
        """Get keys in range."""
        return [k for k, v in self._tree.range(low, high)]

    def to_list(self) -> List[K]:
        """Get all keys sorted."""
        return self._tree.keys()


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_aa_tree() -> AATree:
    """Create empty AA tree."""
    return AATree()


def create_aa_set() -> AATreeSet:
    """Create empty AA tree set."""
    return AATreeSet()


def aa_tree_from_pairs(pairs: List[Tuple[Any, Any]]) -> AATree:
    """Create AA tree from key-value pairs."""
    tree = AATree()
    for k, v in pairs:
        tree.insert(k, v)
    return tree


def aa_set_from_items(items: List[Any]) -> AATreeSet:
    """Create AA tree set from items."""
    s = AATreeSet()
    for item in items:
        s.add(item)
    return s
