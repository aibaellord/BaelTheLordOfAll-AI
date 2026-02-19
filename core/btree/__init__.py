"""
BAEL B-Tree Engine Implementation
==================================

Disk-optimized balanced tree structure.

"Ba'el stores wisdom in perfectly balanced trees." — Ba'el
"""

import logging
import threading
from bisect import bisect_left, bisect_right
from typing import Any, Dict, Generic, Iterator, List, Optional, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.BTree")

K = TypeVar('K')  # Key type
V = TypeVar('V')  # Value type


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class BTreeConfig:
    """B-Tree configuration."""
    order: int = 128  # Maximum children per node (typically large for disk)
    min_degree: Optional[int] = None  # Minimum degree (calculated from order)

    def __post_init__(self):
        if self.min_degree is None:
            self.min_degree = self.order // 2


class BTreeNode(Generic[K, V]):
    """B-Tree node."""

    def __init__(self, leaf: bool = True):
        """Initialize node."""
        self.keys: List[K] = []
        self.values: List[V] = []  # Only for leaf nodes
        self.children: List['BTreeNode[K, V]'] = []
        self.leaf = leaf
        self.parent: Optional['BTreeNode[K, V]'] = None

    @property
    def is_full(self) -> bool:
        """Check if node is full."""
        return len(self.keys) >= self._max_keys

    @property
    def _max_keys(self) -> int:
        """Maximum keys in node."""
        return 2 * 64 - 1  # Default, overridden by tree

    def __repr__(self) -> str:
        return f"BTreeNode(keys={self.keys}, leaf={self.leaf})"


@dataclass
class BTreeStats:
    """B-Tree statistics."""
    node_count: int = 0
    leaf_count: int = 0
    internal_count: int = 0
    height: int = 0
    key_count: int = 0
    splits: int = 0
    merges: int = 0


# ============================================================================
# B-TREE ENGINE
# ============================================================================

class BTreeEngine(Generic[K, V]):
    """
    B-Tree implementation.

    Features:
    - Configurable order
    - Range queries
    - Iteration support
    - Statistics tracking

    "Ba'el maintains perfect balance in all trees." — Ba'el
    """

    def __init__(self, config: Optional[BTreeConfig] = None):
        """Initialize B-Tree."""
        self.config = config or BTreeConfig()
        self.min_degree = self.config.min_degree or (self.config.order // 2)

        self.root: BTreeNode[K, V] = BTreeNode(leaf=True)

        self._stats = BTreeStats()
        self._stats.node_count = 1
        self._stats.leaf_count = 1

        self._lock = threading.RLock()

        logger.info(
            f"B-Tree initialized (order={self.config.order}, "
            f"min_degree={self.min_degree})"
        )

    # ========================================================================
    # BASIC OPERATIONS
    # ========================================================================

    def search(self, key: K) -> Optional[V]:
        """
        Search for a key.

        Args:
            key: Key to search

        Returns:
            Value if found, None otherwise
        """
        with self._lock:
            node, idx = self._search_node(self.root, key)

            if node and idx is not None and idx < len(node.keys) and node.keys[idx] == key:
                return node.values[idx] if node.leaf else None

            return None

    def _search_node(
        self,
        node: BTreeNode[K, V],
        key: K
    ) -> Tuple[Optional[BTreeNode[K, V]], Optional[int]]:
        """Search for key in subtree."""
        i = bisect_left(node.keys, key)

        if i < len(node.keys) and node.keys[i] == key:
            return node, i

        if node.leaf:
            return node, i

        return self._search_node(node.children[i], key)

    def insert(self, key: K, value: V) -> None:
        """
        Insert key-value pair.

        Args:
            key: Key to insert
            value: Value to insert
        """
        with self._lock:
            root = self.root

            if len(root.keys) == 2 * self.min_degree - 1:
                # Root is full, split it
                new_root: BTreeNode[K, V] = BTreeNode(leaf=False)
                new_root.children.append(root)
                root.parent = new_root
                self.root = new_root

                self._split_child(new_root, 0)
                self._insert_non_full(new_root, key, value)

                self._stats.internal_count += 1
                self._stats.height += 1
            else:
                self._insert_non_full(root, key, value)

    def _insert_non_full(
        self,
        node: BTreeNode[K, V],
        key: K,
        value: V
    ) -> None:
        """Insert into non-full node."""
        i = bisect_left(node.keys, key)

        # Check for duplicate
        if i < len(node.keys) and node.keys[i] == key:
            # Update existing
            if node.leaf:
                node.values[i] = value
            return

        if node.leaf:
            node.keys.insert(i, key)
            node.values.insert(i, value)
            self._stats.key_count += 1
        else:
            if len(node.children[i].keys) == 2 * self.min_degree - 1:
                self._split_child(node, i)
                if key > node.keys[i]:
                    i += 1
            self._insert_non_full(node.children[i], key, value)

    def _split_child(self, parent: BTreeNode[K, V], i: int) -> None:
        """Split a full child."""
        t = self.min_degree
        child = parent.children[i]

        # Create new node
        new_node: BTreeNode[K, V] = BTreeNode(leaf=child.leaf)
        new_node.parent = parent

        # Move keys
        mid_idx = t - 1
        parent.keys.insert(i, child.keys[mid_idx])

        # Move right half to new node
        new_node.keys = child.keys[t:]
        child.keys = child.keys[:mid_idx]

        if child.leaf:
            parent.values.insert(i, child.values[mid_idx])
            new_node.values = child.values[t:]
            child.values = child.values[:mid_idx]
        else:
            new_node.children = child.children[t:]
            child.children = child.children[:t]

            for c in new_node.children:
                c.parent = new_node

        parent.children.insert(i + 1, new_node)

        self._stats.splits += 1
        self._stats.node_count += 1
        if new_node.leaf:
            self._stats.leaf_count += 1
        else:
            self._stats.internal_count += 1

    def delete(self, key: K) -> bool:
        """
        Delete a key.

        Args:
            key: Key to delete

        Returns:
            True if deleted
        """
        with self._lock:
            result = self._delete(self.root, key)

            # Shrink tree if root is empty
            if not self.root.keys and self.root.children:
                self.root = self.root.children[0]
                self.root.parent = None
                self._stats.height -= 1
                self._stats.internal_count -= 1
                self._stats.node_count -= 1

            return result

    def _delete(self, node: BTreeNode[K, V], key: K) -> bool:
        """Delete key from subtree."""
        t = self.min_degree
        i = bisect_left(node.keys, key)

        if i < len(node.keys) and node.keys[i] == key:
            # Found key in this node
            if node.leaf:
                node.keys.pop(i)
                node.values.pop(i)
                self._stats.key_count -= 1
                return True
            else:
                # Internal node
                return self._delete_internal(node, i)
        else:
            # Key not in this node
            if node.leaf:
                return False

            # Ensure child has enough keys
            if len(node.children[i].keys) < t:
                self._fill_child(node, i)

            # Recalculate index after potential merge
            if i > len(node.keys):
                i -= 1

            return self._delete(node.children[i], key)

    def _delete_internal(self, node: BTreeNode[K, V], i: int) -> bool:
        """Delete from internal node."""
        t = self.min_degree

        if len(node.children[i].keys) >= t:
            # Get predecessor
            pred = self._get_predecessor(node.children[i])
            node.keys[i] = pred
            return self._delete(node.children[i], pred)

        elif len(node.children[i + 1].keys) >= t:
            # Get successor
            succ = self._get_successor(node.children[i + 1])
            node.keys[i] = succ
            return self._delete(node.children[i + 1], succ)

        else:
            # Merge children
            self._merge_children(node, i)
            return self._delete(node.children[i], node.keys[i])

    def _get_predecessor(self, node: BTreeNode[K, V]) -> K:
        """Get predecessor key."""
        while not node.leaf:
            node = node.children[-1]
        return node.keys[-1]

    def _get_successor(self, node: BTreeNode[K, V]) -> K:
        """Get successor key."""
        while not node.leaf:
            node = node.children[0]
        return node.keys[0]

    def _fill_child(self, node: BTreeNode[K, V], i: int) -> None:
        """Ensure child has minimum keys."""
        t = self.min_degree

        if i > 0 and len(node.children[i - 1].keys) >= t:
            self._borrow_from_prev(node, i)
        elif i < len(node.children) - 1 and len(node.children[i + 1].keys) >= t:
            self._borrow_from_next(node, i)
        else:
            if i < len(node.children) - 1:
                self._merge_children(node, i)
            else:
                self._merge_children(node, i - 1)

    def _borrow_from_prev(self, node: BTreeNode[K, V], i: int) -> None:
        """Borrow key from previous sibling."""
        child = node.children[i]
        sibling = node.children[i - 1]

        child.keys.insert(0, node.keys[i - 1])
        node.keys[i - 1] = sibling.keys.pop()

        if child.leaf:
            child.values.insert(0, node.values[i - 1] if i - 1 < len(node.values) else None)
            if sibling.values:
                sibling.values.pop()
        else:
            child.children.insert(0, sibling.children.pop())
            child.children[0].parent = child

    def _borrow_from_next(self, node: BTreeNode[K, V], i: int) -> None:
        """Borrow key from next sibling."""
        child = node.children[i]
        sibling = node.children[i + 1]

        child.keys.append(node.keys[i])
        node.keys[i] = sibling.keys.pop(0)

        if child.leaf:
            if sibling.values:
                child.values.append(sibling.values.pop(0))
        else:
            child.children.append(sibling.children.pop(0))
            child.children[-1].parent = child

    def _merge_children(self, node: BTreeNode[K, V], i: int) -> None:
        """Merge child with next sibling."""
        left = node.children[i]
        right = node.children[i + 1]

        # Move key from parent
        left.keys.append(node.keys.pop(i))

        # Move all from right
        left.keys.extend(right.keys)

        if left.leaf:
            left.values.extend(right.values)
        else:
            left.children.extend(right.children)
            for c in right.children:
                c.parent = left

        node.children.pop(i + 1)

        self._stats.merges += 1
        self._stats.node_count -= 1
        if right.leaf:
            self._stats.leaf_count -= 1
        else:
            self._stats.internal_count -= 1

    # ========================================================================
    # RANGE QUERIES
    # ========================================================================

    def range(
        self,
        start: Optional[K] = None,
        end: Optional[K] = None,
        inclusive: bool = True
    ) -> Iterator[Tuple[K, V]]:
        """
        Range query.

        Args:
            start: Start key (inclusive)
            end: End key (inclusive or exclusive)
            inclusive: Whether end is inclusive

        Yields:
            (key, value) pairs in range
        """
        with self._lock:
            for key, value in self._iterate_range(self.root, start, end, inclusive):
                yield key, value

    def _iterate_range(
        self,
        node: BTreeNode[K, V],
        start: Optional[K],
        end: Optional[K],
        inclusive: bool
    ) -> Iterator[Tuple[K, V]]:
        """Iterate keys in range."""
        if node.leaf:
            for i, key in enumerate(node.keys):
                if start is not None and key < start:
                    continue
                if end is not None:
                    if inclusive and key > end:
                        break
                    if not inclusive and key >= end:
                        break
                yield key, node.values[i]
        else:
            for i, key in enumerate(node.keys):
                # Recurse into left child if needed
                if start is None or key >= start:
                    if i < len(node.children):
                        yield from self._iterate_range(
                            node.children[i], start, end, inclusive
                        )

                # Yield current key if in range
                if start is not None and key < start:
                    continue
                if end is not None:
                    if inclusive and key > end:
                        break
                    if not inclusive and key >= end:
                        break

                # For internal nodes, we need to handle this differently
                if not node.leaf and i < len(node.values):
                    yield key, node.values[i]

            # Recurse into last child
            if node.children:
                yield from self._iterate_range(
                    node.children[-1], start, end, inclusive
                )

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def __contains__(self, key: K) -> bool:
        """Check if key exists."""
        return self.search(key) is not None

    def __getitem__(self, key: K) -> V:
        """Get value by key."""
        value = self.search(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key: K, value: V) -> None:
        """Set value by key."""
        self.insert(key, value)

    def __delitem__(self, key: K) -> None:
        """Delete by key."""
        if not self.delete(key):
            raise KeyError(key)

    def __len__(self) -> int:
        """Get number of keys."""
        return self._stats.key_count

    def __iter__(self) -> Iterator[K]:
        """Iterate all keys."""
        for key, _ in self.range():
            yield key

    def items(self) -> Iterator[Tuple[K, V]]:
        """Iterate all items."""
        return self.range()

    def keys(self) -> Iterator[K]:
        """Iterate all keys."""
        return iter(self)

    def values(self) -> Iterator[V]:
        """Iterate all values."""
        for _, value in self.range():
            yield value

    def min_key(self) -> Optional[K]:
        """Get minimum key."""
        node = self.root
        while node.children:
            node = node.children[0]
        return node.keys[0] if node.keys else None

    def max_key(self) -> Optional[K]:
        """Get maximum key."""
        node = self.root
        while node.children:
            node = node.children[-1]
        return node.keys[-1] if node.keys else None

    def get_height(self) -> int:
        """Get tree height."""
        height = 0
        node = self.root
        while node.children:
            height += 1
            node = node.children[0]
        return height

    def get_stats(self) -> Dict[str, Any]:
        """Get tree statistics."""
        return {
            'key_count': self._stats.key_count,
            'node_count': self._stats.node_count,
            'leaf_count': self._stats.leaf_count,
            'internal_count': self._stats.internal_count,
            'height': self.get_height(),
            'splits': self._stats.splits,
            'merges': self._stats.merges,
            'order': self.config.order,
            'min_degree': self.min_degree
        }

    def clear(self) -> None:
        """Clear all data."""
        with self._lock:
            self.root = BTreeNode(leaf=True)
            self._stats = BTreeStats()
            self._stats.node_count = 1
            self._stats.leaf_count = 1


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_btree(
    order: int = 128,
    **kwargs
) -> BTreeEngine:
    """Create a new B-Tree."""
    config = BTreeConfig(order=order, **kwargs)
    return BTreeEngine(config)


def create_small_btree() -> BTreeEngine:
    """Create a small B-Tree (order 4) for testing."""
    return create_btree(order=4)


def create_disk_btree() -> BTreeEngine:
    """Create a disk-optimized B-Tree (large order)."""
    return create_btree(order=256)
