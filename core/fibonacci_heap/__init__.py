"""
BAEL Fibonacci Heap Engine
==========================

Amortized O(1) decrease-key priority queue.

"Ba'el heaps with Fibonacci elegance." — Ba'el
"""

import logging
import threading
import math
from typing import Any, Dict, List, Optional, Tuple, Generic, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger("BAEL.FibonacciHeap")


K = TypeVar('K')  # Key/priority type
V = TypeVar('V')  # Value type


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class FibHeapStats:
    """Fibonacci heap statistics."""
    size: int
    num_trees: int
    max_degree: int
    num_marked: int


class FibNode(Generic[K, V]):
    """Node in Fibonacci Heap."""

    __slots__ = [
        'key', 'value', 'degree', 'marked',
        'parent', 'child', 'left', 'right'
    ]

    def __init__(self, key: K, value: V):
        self.key = key
        self.value = value
        self.degree = 0
        self.marked = False
        self.parent: Optional['FibNode[K, V]'] = None
        self.child: Optional['FibNode[K, V]'] = None
        self.left: 'FibNode[K, V]' = self
        self.right: 'FibNode[K, V]' = self


# ============================================================================
# FIBONACCI HEAP
# ============================================================================

class FibonacciHeap(Generic[K, V]):
    """
    Fibonacci Heap: optimal amortized priority queue.

    Time complexities (amortized):
    - insert: O(1)
    - find_min: O(1)
    - merge: O(1)
    - extract_min: O(log n)
    - decrease_key: O(1)
    - delete: O(log n)

    Optimal for Dijkstra's algorithm.

    "Ba'el prioritizes with golden efficiency." — Ba'el
    """

    def __init__(self):
        """Initialize empty Fibonacci Heap."""
        self._min: Optional[FibNode[K, V]] = None
        self._size = 0
        self._lock = threading.RLock()

    def _add_to_root_list(self, node: FibNode[K, V]):
        """Add node to root list."""
        if self._min is None:
            self._min = node
            node.left = node
            node.right = node
        else:
            # Insert to right of min
            node.right = self._min.right
            node.left = self._min
            self._min.right.left = node
            self._min.right = node

    def _remove_from_list(self, node: FibNode[K, V]):
        """Remove node from its doubly-linked list."""
        node.left.right = node.right
        node.right.left = node.left

    def _link(self, child: FibNode[K, V], parent: FibNode[K, V]):
        """Link child under parent."""
        self._remove_from_list(child)

        child.parent = parent
        child.marked = False

        if parent.child is None:
            parent.child = child
            child.left = child
            child.right = child
        else:
            child.right = parent.child.right
            child.left = parent.child
            parent.child.right.left = child
            parent.child.right = child

        parent.degree += 1

    def insert(self, key: K, value: V) -> FibNode[K, V]:
        """
        Insert key-value pair.

        O(1) amortized.
        Returns node handle for decrease_key.
        """
        with self._lock:
            node = FibNode(key, value)
            self._add_to_root_list(node)

            if self._min is None or key < self._min.key:
                self._min = node

            self._size += 1
            return node

    def find_min(self) -> Optional[Tuple[K, V]]:
        """
        Get minimum key-value pair.

        O(1).
        """
        with self._lock:
            if self._min is None:
                return None
            return (self._min.key, self._min.value)

    def extract_min(self) -> Optional[Tuple[K, V]]:
        """
        Remove and return minimum.

        O(log n) amortized.
        """
        with self._lock:
            z = self._min
            if z is None:
                return None

            # Add children to root list
            if z.child:
                child = z.child
                children = []
                while True:
                    children.append(child)
                    child = child.right
                    if child == z.child:
                        break

                for child in children:
                    self._add_to_root_list(child)
                    child.parent = None

            # Remove z from root list
            self._remove_from_list(z)

            if z == z.right:
                self._min = None
            else:
                self._min = z.right
                self._consolidate()

            self._size -= 1
            return (z.key, z.value)

    def _consolidate(self):
        """Consolidate trees after extract_min."""
        max_degree = int(math.log2(self._size)) + 1
        A = [None] * (max_degree + 1)

        # Collect root nodes
        roots = []
        node = self._min
        while True:
            roots.append(node)
            node = node.right
            if node == self._min:
                break

        for w in roots:
            x = w
            d = x.degree

            while d < len(A) and A[d] is not None:
                y = A[d]
                if x.key > y.key:
                    x, y = y, x
                self._link(y, x)
                A[d] = None
                d += 1

            if d >= len(A):
                A.extend([None] * (d - len(A) + 1))
            A[d] = x

        # Rebuild root list
        self._min = None
        for node in A:
            if node is not None:
                if self._min is None:
                    self._min = node
                    node.left = node
                    node.right = node
                else:
                    self._add_to_root_list(node)
                    if node.key < self._min.key:
                        self._min = node

    def decrease_key(self, node: FibNode[K, V], new_key: K):
        """
        Decrease key of node.

        O(1) amortized.
        """
        with self._lock:
            if new_key > node.key:
                raise ValueError("New key is greater than current key")

            node.key = new_key
            parent = node.parent

            if parent is not None and node.key < parent.key:
                self._cut(node, parent)
                self._cascading_cut(parent)

            if node.key < self._min.key:
                self._min = node

    def _cut(self, node: FibNode[K, V], parent: FibNode[K, V]):
        """Cut node from parent and add to root list."""
        # Remove from parent's child list
        if node.right == node:
            parent.child = None
        else:
            if parent.child == node:
                parent.child = node.right
            self._remove_from_list(node)

        parent.degree -= 1

        # Add to root list
        self._add_to_root_list(node)
        node.parent = None
        node.marked = False

    def _cascading_cut(self, node: FibNode[K, V]):
        """Cascading cut after decrease_key."""
        parent = node.parent
        if parent is not None:
            if not node.marked:
                node.marked = True
            else:
                self._cut(node, parent)
                self._cascading_cut(parent)

    def delete(self, node: FibNode[K, V]):
        """
        Delete node from heap.

        O(log n) amortized.
        """
        with self._lock:
            # Decrease to negative infinity (represented by extracting after making min)
            self.decrease_key(node, float('-inf'))
            self.extract_min()

    def merge(self, other: 'FibonacciHeap[K, V]'):
        """
        Merge other heap into this one.

        O(1).
        """
        with self._lock:
            if other._min is None:
                return

            if self._min is None:
                self._min = other._min
            else:
                # Concatenate root lists
                self._min.right.left = other._min.left
                other._min.left.right = self._min.right
                self._min.right = other._min
                other._min.left = self._min

                if other._min.key < self._min.key:
                    self._min = other._min

            self._size += other._size
            other._min = None
            other._size = 0

    def __len__(self) -> int:
        return self._size

    def __bool__(self) -> bool:
        return self._size > 0

    def is_empty(self) -> bool:
        """Check if heap is empty."""
        return self._size == 0

    # Statistics

    def get_stats(self) -> FibHeapStats:
        """Get heap statistics."""
        with self._lock:
            if self._min is None:
                return FibHeapStats(0, 0, 0, 0)

            num_trees = 0
            max_degree = 0
            num_marked = 0

            def count_marked(node):
                if node is None:
                    return 0
                count = 1 if node.marked else 0
                if node.child:
                    child = node.child
                    while True:
                        count += count_marked(child)
                        child = child.right
                        if child == node.child:
                            break
                return count

            node = self._min
            while True:
                num_trees += 1
                max_degree = max(max_degree, node.degree)
                num_marked += count_marked(node)
                node = node.right
                if node == self._min:
                    break

            return FibHeapStats(
                size=self._size,
                num_trees=num_trees,
                max_degree=max_degree,
                num_marked=num_marked
            )


# ============================================================================
# BINOMIAL HEAP
# ============================================================================

class BinomialNode(Generic[K, V]):
    """Node in Binomial Heap."""

    __slots__ = ['key', 'value', 'degree', 'parent', 'child', 'sibling']

    def __init__(self, key: K, value: V):
        self.key = key
        self.value = value
        self.degree = 0
        self.parent: Optional['BinomialNode[K, V]'] = None
        self.child: Optional['BinomialNode[K, V]'] = None
        self.sibling: Optional['BinomialNode[K, V]'] = None


class BinomialHeap(Generic[K, V]):
    """
    Binomial Heap: mergeable priority queue.

    Time complexities:
    - insert: O(log n)
    - find_min: O(log n)
    - merge: O(log n)
    - extract_min: O(log n)

    "Ba'el binds heaps together." — Ba'el
    """

    def __init__(self):
        """Initialize empty Binomial Heap."""
        self._head: Optional[BinomialNode[K, V]] = None
        self._size = 0
        self._lock = threading.RLock()

    def _link(self, y: BinomialNode[K, V], z: BinomialNode[K, V]):
        """Link y under z (same degree trees)."""
        y.parent = z
        y.sibling = z.child
        z.child = y
        z.degree += 1

    def _merge_lists(
        self,
        h1: Optional[BinomialNode[K, V]],
        h2: Optional[BinomialNode[K, V]]
    ) -> Optional[BinomialNode[K, V]]:
        """Merge two root lists by degree."""
        if h1 is None:
            return h2
        if h2 is None:
            return h1

        # Merge by degree
        if h1.degree <= h2.degree:
            head = h1
            h1 = h1.sibling
        else:
            head = h2
            h2 = h2.sibling

        current = head

        while h1 and h2:
            if h1.degree <= h2.degree:
                current.sibling = h1
                h1 = h1.sibling
            else:
                current.sibling = h2
                h2 = h2.sibling
            current = current.sibling

        current.sibling = h1 if h1 else h2

        return head

    def merge(self, other: 'BinomialHeap[K, V]'):
        """
        Merge other heap into this one.

        O(log n).
        """
        with self._lock:
            h = self._merge_lists(self._head, other._head)

            if h is None:
                return

            prev = None
            x = h
            next_x = x.sibling

            while next_x:
                if (x.degree != next_x.degree or
                    (next_x.sibling and next_x.sibling.degree == x.degree)):
                    prev = x
                    x = next_x
                elif x.key <= next_x.key:
                    x.sibling = next_x.sibling
                    self._link(next_x, x)
                else:
                    if prev is None:
                        h = next_x
                    else:
                        prev.sibling = next_x
                    self._link(x, next_x)
                    x = next_x

                next_x = x.sibling

            self._head = h
            self._size += other._size
            other._head = None
            other._size = 0

    def insert(self, key: K, value: V):
        """Insert key-value pair. O(log n)."""
        with self._lock:
            node = BinomialNode(key, value)
            temp = BinomialHeap()
            temp._head = node
            temp._size = 1
            self.merge(temp)

    def find_min(self) -> Optional[Tuple[K, V]]:
        """Get minimum. O(log n)."""
        with self._lock:
            if self._head is None:
                return None

            min_node = self._head
            current = self._head.sibling

            while current:
                if current.key < min_node.key:
                    min_node = current
                current = current.sibling

            return (min_node.key, min_node.value)

    def extract_min(self) -> Optional[Tuple[K, V]]:
        """Extract minimum. O(log n)."""
        with self._lock:
            if self._head is None:
                return None

            # Find minimum
            min_node = self._head
            min_prev = None
            prev = None
            current = self._head

            while current:
                if current.key < min_node.key:
                    min_node = current
                    min_prev = prev
                prev = current
                current = current.sibling

            # Remove min from root list
            if min_prev is None:
                self._head = min_node.sibling
            else:
                min_prev.sibling = min_node.sibling

            # Reverse children and merge
            child_list = None
            child = min_node.child
            while child:
                next_child = child.sibling
                child.sibling = child_list
                child.parent = None
                child_list = child
                child = next_child

            temp = BinomialHeap()
            temp._head = child_list
            self.merge(temp)

            self._size -= 1
            return (min_node.key, min_node.value)

    def __len__(self) -> int:
        return self._size

    def is_empty(self) -> bool:
        return self._size == 0


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_fibonacci_heap() -> FibonacciHeap:
    """Create empty Fibonacci Heap."""
    return FibonacciHeap()


def create_binomial_heap() -> BinomialHeap:
    """Create empty Binomial Heap."""
    return BinomialHeap()


def dijkstra_with_fib_heap(
    adj: Dict[int, List[Tuple[int, float]]],
    source: int
) -> Dict[int, float]:
    """
    Dijkstra's algorithm using Fibonacci Heap.

    O(E + V log V) - optimal for dense graphs.
    """
    dist = {source: 0}
    heap = FibonacciHeap()
    nodes = {source: heap.insert(0, source)}

    while heap:
        d, u = heap.extract_min()

        if u not in adj:
            continue

        for v, w in adj[u]:
            alt = d + w
            if v not in dist or alt < dist[v]:
                dist[v] = alt
                if v in nodes:
                    heap.decrease_key(nodes[v], alt)
                else:
                    nodes[v] = heap.insert(alt, v)

    return dist
