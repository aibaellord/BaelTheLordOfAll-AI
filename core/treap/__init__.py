"""
BAEL Treap Engine Implementation
=================================

Randomized binary search tree.

"Ba'el merges tree and heap into perfect balance." — Ba'el
"""

import logging
import random
import threading
from typing import Any, Callable, Dict, Generic, Iterator, List, Optional, Tuple, TypeVar
from dataclasses import dataclass, field

logger = logging.getLogger("BAEL.Treap")

K = TypeVar('K')  # Key type (must be comparable)
V = TypeVar('V')  # Value type


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class TreapNode(Generic[K, V]):
    """Node in treap."""

    def __init__(
        self,
        key: K,
        value: V,
        priority: Optional[float] = None
    ):
        """Initialize node."""
        self.key = key
        self.value = value
        self.priority = priority if priority is not None else random.random()

        self.left: Optional['TreapNode[K, V]'] = None
        self.right: Optional['TreapNode[K, V]'] = None

        # Subtree size for order statistics
        self.size = 1

    def update_size(self) -> None:
        """Update subtree size."""
        self.size = 1
        if self.left:
            self.size += self.left.size
        if self.right:
            self.size += self.right.size


@dataclass
class TreapStats:
    """Treap statistics."""
    node_count: int = 0
    rotations: int = 0
    splits: int = 0
    merges: int = 0


# ============================================================================
# TREAP ENGINE
# ============================================================================

class TreapEngine(Generic[K, V]):
    """
    Treap (Tree + Heap) implementation.

    Features:
    - O(log n) expected time operations
    - Randomized balancing
    - Split and merge operations
    - Order statistics

    "Ba'el maintains random balance through divine priority." — Ba'el
    """

    def __init__(self):
        """Initialize treap."""
        self.root: Optional[TreapNode[K, V]] = None
        self._stats = TreapStats()
        self._lock = threading.RLock()

        logger.info("Treap initialized")

    # ========================================================================
    # ROTATIONS
    # ========================================================================

    def _rotate_right(self, node: TreapNode[K, V]) -> TreapNode[K, V]:
        """Rotate right around node."""
        self._stats.rotations += 1

        left = node.left
        node.left = left.right
        left.right = node

        node.update_size()
        left.update_size()

        return left

    def _rotate_left(self, node: TreapNode[K, V]) -> TreapNode[K, V]:
        """Rotate left around node."""
        self._stats.rotations += 1

        right = node.right
        node.right = right.left
        right.left = node

        node.update_size()
        right.update_size()

        return right

    # ========================================================================
    # BASIC OPERATIONS
    # ========================================================================

    def insert(self, key: K, value: V) -> None:
        """
        Insert key-value pair.

        Args:
            key: Key
            value: Value
        """
        with self._lock:
            self.root = self._insert(self.root, key, value)
            self._stats.node_count += 1

    def _insert(
        self,
        node: Optional[TreapNode[K, V]],
        key: K,
        value: V
    ) -> TreapNode[K, V]:
        """Recursive insert."""
        if node is None:
            return TreapNode(key, value)

        if key < node.key:
            node.left = self._insert(node.left, key, value)

            if node.left.priority > node.priority:
                node = self._rotate_right(node)
        elif key > node.key:
            node.right = self._insert(node.right, key, value)

            if node.right.priority > node.priority:
                node = self._rotate_left(node)
        else:
            # Update existing key
            node.value = value
            self._stats.node_count -= 1  # Correct count

        node.update_size()
        return node

    def delete(self, key: K) -> bool:
        """
        Delete key.

        Args:
            key: Key to delete

        Returns:
            True if deleted
        """
        with self._lock:
            old_count = self._stats.node_count
            self.root = self._delete(self.root, key)

            if self._stats.node_count < old_count:
                self._stats.node_count -= 1
                return True
            return False

    def _delete(
        self,
        node: Optional[TreapNode[K, V]],
        key: K
    ) -> Optional[TreapNode[K, V]]:
        """Recursive delete."""
        if node is None:
            return None

        if key < node.key:
            node.left = self._delete(node.left, key)
        elif key > node.key:
            node.right = self._delete(node.right, key)
        else:
            # Found node to delete
            if node.left is None:
                return node.right
            elif node.right is None:
                return node.left
            else:
                # Rotate down and delete
                if node.left.priority > node.right.priority:
                    node = self._rotate_right(node)
                    node.right = self._delete(node.right, key)
                else:
                    node = self._rotate_left(node)
                    node.left = self._delete(node.left, key)

        if node:
            node.update_size()
        return node

    def get(self, key: K) -> Optional[V]:
        """
        Get value for key.

        Args:
            key: Key to search

        Returns:
            Value or None
        """
        with self._lock:
            node = self._find(self.root, key)
            return node.value if node else None

    def _find(
        self,
        node: Optional[TreapNode[K, V]],
        key: K
    ) -> Optional[TreapNode[K, V]]:
        """Find node by key."""
        if node is None:
            return None

        if key < node.key:
            return self._find(node.left, key)
        elif key > node.key:
            return self._find(node.right, key)
        else:
            return node

    def contains(self, key: K) -> bool:
        """Check if key exists."""
        return self.get(key) is not None

    # ========================================================================
    # SPLIT AND MERGE
    # ========================================================================

    def split(
        self,
        key: K
    ) -> Tuple['TreapEngine[K, V]', 'TreapEngine[K, V]']:
        """
        Split treap by key.

        Args:
            key: Split key

        Returns:
            (left_treap, right_treap) where left < key and right >= key
        """
        with self._lock:
            self._stats.splits += 1

            left_root, right_root = self._split(self.root, key)

            left = TreapEngine()
            left.root = left_root
            left._stats.node_count = self._count_nodes(left_root)

            right = TreapEngine()
            right.root = right_root
            right._stats.node_count = self._count_nodes(right_root)

            return left, right

    def _split(
        self,
        node: Optional[TreapNode[K, V]],
        key: K
    ) -> Tuple[Optional[TreapNode[K, V]], Optional[TreapNode[K, V]]]:
        """Recursive split."""
        if node is None:
            return None, None

        if key <= node.key:
            left, node.left = self._split(node.left, key)
            node.update_size()
            return left, node
        else:
            node.right, right = self._split(node.right, key)
            node.update_size()
            return node, right

    def merge(self, other: 'TreapEngine[K, V]') -> None:
        """
        Merge another treap into this one.
        Assumes all keys in other are greater than all keys in self.

        Args:
            other: Treap to merge
        """
        with self._lock:
            self._stats.merges += 1
            self.root = self._merge(self.root, other.root)
            self._stats.node_count = self._count_nodes(self.root)

    def _merge(
        self,
        left: Optional[TreapNode[K, V]],
        right: Optional[TreapNode[K, V]]
    ) -> Optional[TreapNode[K, V]]:
        """Recursive merge."""
        if left is None:
            return right
        if right is None:
            return left

        if left.priority > right.priority:
            left.right = self._merge(left.right, right)
            left.update_size()
            return left
        else:
            right.left = self._merge(left, right.left)
            right.update_size()
            return right

    def _count_nodes(self, node: Optional[TreapNode[K, V]]) -> int:
        """Count nodes in subtree."""
        return node.size if node else 0

    # ========================================================================
    # ORDER STATISTICS
    # ========================================================================

    def kth_element(self, k: int) -> Optional[Tuple[K, V]]:
        """
        Get k-th smallest element (1-indexed).

        Args:
            k: Rank (1-indexed)

        Returns:
            (key, value) or None
        """
        if k < 1 or k > len(self):
            return None

        with self._lock:
            node = self._kth_element(self.root, k)
            return (node.key, node.value) if node else None

    def _kth_element(
        self,
        node: Optional[TreapNode[K, V]],
        k: int
    ) -> Optional[TreapNode[K, V]]:
        """Find k-th element."""
        if node is None:
            return None

        left_size = node.left.size if node.left else 0

        if k <= left_size:
            return self._kth_element(node.left, k)
        elif k == left_size + 1:
            return node
        else:
            return self._kth_element(node.right, k - left_size - 1)

    def rank(self, key: K) -> int:
        """
        Get rank of key (1-indexed).

        Args:
            key: Key to find rank of

        Returns:
            Rank (number of elements less than key + 1)
        """
        with self._lock:
            return self._rank(self.root, key) + 1

    def _rank(
        self,
        node: Optional[TreapNode[K, V]],
        key: K
    ) -> int:
        """Get rank in subtree."""
        if node is None:
            return 0

        if key <= node.key:
            return self._rank(node.left, key)
        else:
            left_size = node.left.size if node.left else 0
            return left_size + 1 + self._rank(node.right, key)

    # ========================================================================
    # RANGE OPERATIONS
    # ========================================================================

    def range(
        self,
        lo: K,
        hi: K
    ) -> List[Tuple[K, V]]:
        """
        Get all key-value pairs in range [lo, hi].

        Args:
            lo: Low bound
            hi: High bound

        Returns:
            List of (key, value) pairs
        """
        result: List[Tuple[K, V]] = []

        with self._lock:
            self._range(self.root, lo, hi, result)

        return result

    def _range(
        self,
        node: Optional[TreapNode[K, V]],
        lo: K,
        hi: K,
        result: List[Tuple[K, V]]
    ) -> None:
        """Collect range in subtree."""
        if node is None:
            return

        if lo <= node.key:
            self._range(node.left, lo, hi, result)

        if lo <= node.key <= hi:
            result.append((node.key, node.value))

        if node.key <= hi:
            self._range(node.right, lo, hi, result)

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def min_key(self) -> Optional[K]:
        """Get minimum key."""
        if self.root is None:
            return None

        node = self.root
        while node.left:
            node = node.left
        return node.key

    def max_key(self) -> Optional[K]:
        """Get maximum key."""
        if self.root is None:
            return None

        node = self.root
        while node.right:
            node = node.right
        return node.key

    def __len__(self) -> int:
        return self._stats.node_count

    def __contains__(self, key: K) -> bool:
        return self.contains(key)

    def __iter__(self) -> Iterator[Tuple[K, V]]:
        """In-order iteration."""
        stack = []
        node = self.root

        while stack or node:
            while node:
                stack.append(node)
                node = node.left

            node = stack.pop()
            yield (node.key, node.value)
            node = node.right

    def keys(self) -> List[K]:
        """Get all keys in sorted order."""
        return [k for k, v in self]

    def values(self) -> List[V]:
        """Get all values in key order."""
        return [v for k, v in self]

    def items(self) -> List[Tuple[K, V]]:
        """Get all items in sorted order."""
        return list(self)

    def clear(self) -> None:
        """Clear treap."""
        with self._lock:
            self.root = None
            self._stats = TreapStats()

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'node_count': self._stats.node_count,
            'rotations': self._stats.rotations,
            'splits': self._stats.splits,
            'merges': self._stats.merges
        }


# ============================================================================
# IMPLICIT TREAP
# ============================================================================

class ImplicitTreapNode(Generic[V]):
    """Node for implicit treap (array-like operations)."""

    def __init__(self, value: V, priority: Optional[float] = None):
        self.value = value
        self.priority = priority if priority is not None else random.random()

        self.left: Optional['ImplicitTreapNode[V]'] = None
        self.right: Optional['ImplicitTreapNode[V]'] = None
        self.size = 1

        # For lazy propagation (reversals)
        self.reversed = False

    def update_size(self) -> None:
        self.size = 1
        if self.left:
            self.size += self.left.size
        if self.right:
            self.size += self.right.size

    def push_down(self) -> None:
        """Push reversed flag down."""
        if self.reversed:
            self.left, self.right = self.right, self.left

            if self.left:
                self.left.reversed = not self.left.reversed
            if self.right:
                self.right.reversed = not self.right.reversed

            self.reversed = False


class ImplicitTreap(Generic[V]):
    """
    Implicit Treap for array operations.

    Supports O(log n) insert, delete, and range reversal.

    "Ba'el indexes arrays without explicit keys." — Ba'el
    """

    def __init__(self):
        self.root: Optional[ImplicitTreapNode[V]] = None
        self._lock = threading.RLock()

    def _get_size(self, node: Optional[ImplicitTreapNode[V]]) -> int:
        return node.size if node else 0

    def _split(
        self,
        node: Optional[ImplicitTreapNode[V]],
        pos: int
    ) -> Tuple[Optional[ImplicitTreapNode[V]], Optional[ImplicitTreapNode[V]]]:
        """Split at position."""
        if node is None:
            return None, None

        node.push_down()

        left_size = self._get_size(node.left)

        if pos <= left_size:
            left, node.left = self._split(node.left, pos)
            node.update_size()
            return left, node
        else:
            node.right, right = self._split(node.right, pos - left_size - 1)
            node.update_size()
            return node, right

    def _merge(
        self,
        left: Optional[ImplicitTreapNode[V]],
        right: Optional[ImplicitTreapNode[V]]
    ) -> Optional[ImplicitTreapNode[V]]:
        """Merge two nodes."""
        if left is None:
            return right
        if right is None:
            return left

        left.push_down()
        right.push_down()

        if left.priority > right.priority:
            left.right = self._merge(left.right, right)
            left.update_size()
            return left
        else:
            right.left = self._merge(left, right.left)
            right.update_size()
            return right

    def insert(self, pos: int, value: V) -> None:
        """Insert at position."""
        with self._lock:
            left, right = self._split(self.root, pos)
            new_node = ImplicitTreapNode(value)
            self.root = self._merge(self._merge(left, new_node), right)

    def delete(self, pos: int) -> Optional[V]:
        """Delete at position."""
        with self._lock:
            left, mid_right = self._split(self.root, pos)
            mid, right = self._split(mid_right, 1)
            self.root = self._merge(left, right)
            return mid.value if mid else None

    def get(self, pos: int) -> Optional[V]:
        """Get value at position."""
        with self._lock:
            left, mid_right = self._split(self.root, pos)
            mid, right = self._split(mid_right, 1)
            result = mid.value if mid else None
            self.root = self._merge(self._merge(left, mid), right)
            return result

    def reverse(self, l: int, r: int) -> None:
        """Reverse range [l, r)."""
        with self._lock:
            left, mid_right = self._split(self.root, l)
            mid, right = self._split(mid_right, r - l)

            if mid:
                mid.reversed = not mid.reversed

            self.root = self._merge(self._merge(left, mid), right)

    def __len__(self) -> int:
        return self._get_size(self.root)

    def to_list(self) -> List[V]:
        """Convert to list."""
        result = []
        self._inorder(self.root, result)
        return result

    def _inorder(
        self,
        node: Optional[ImplicitTreapNode[V]],
        result: List[V]
    ) -> None:
        if node is None:
            return

        node.push_down()
        self._inorder(node.left, result)
        result.append(node.value)
        self._inorder(node.right, result)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_treap() -> TreapEngine:
    """Create a new treap."""
    return TreapEngine()


def create_implicit_treap() -> ImplicitTreap:
    """Create an implicit treap."""
    return ImplicitTreap()


def from_dict(data: Dict[K, V]) -> TreapEngine[K, V]:
    """Create treap from dictionary."""
    treap = TreapEngine()
    for key, value in data.items():
        treap.insert(key, value)
    return treap
