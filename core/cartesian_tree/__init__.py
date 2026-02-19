"""
BAEL Cartesian Tree Engine
==========================

Tree with heap and BST properties for RMQ.

"Ba'el builds the tree that serves two masters." — Ba'el
"""

import logging
import threading
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar
from dataclasses import dataclass, field

logger = logging.getLogger("BAEL.CartesianTree")

T = TypeVar('T')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class CartesianNode(Generic[T]):
    """Cartesian tree node."""
    index: int
    value: T
    left: Optional['CartesianNode[T]'] = None
    right: Optional['CartesianNode[T]'] = None
    parent: Optional['CartesianNode[T]'] = None


@dataclass
class CartesianStats:
    """Cartesian tree statistics."""
    size: int = 0
    height: int = 0
    builds: int = 0
    queries: int = 0


# ============================================================================
# CARTESIAN TREE ENGINE
# ============================================================================

class CartesianTreeEngine(Generic[T]):
    """
    Cartesian Tree for Range Minimum Queries.

    Properties:
    - Min-heap on values (parent <= children)
    - BST on indices (in-order = original array order)
    - O(n) construction
    - O(1) RMQ with LCA preprocessing

    "Ba'el unifies heap and tree in perfect balance." — Ba'el
    """

    def __init__(
        self,
        compare: Callable[[T, T], bool] = lambda a, b: a < b
    ):
        """
        Initialize Cartesian tree.

        Args:
            compare: Comparison function (a, b) -> True if a has higher priority
        """
        self._compare = compare
        self._root: Optional[CartesianNode[T]] = None
        self._array: List[T] = []
        self._nodes: List[Optional[CartesianNode[T]]] = []
        self._stats = CartesianStats()
        self._lock = threading.RLock()

        # For O(1) RMQ
        self._euler_tour: List[int] = []
        self._first_occurrence: List[int] = []
        self._sparse_table: List[List[int]] = []
        self._log_table: List[int] = []

        logger.debug("Cartesian tree initialized")

    # ========================================================================
    # BUILD
    # ========================================================================

    def build(self, array: List[T]) -> Optional[CartesianNode[T]]:
        """
        Build Cartesian tree from array in O(n).

        Args:
            array: Input array

        Returns:
            Root node
        """
        with self._lock:
            self._array = list(array)
            self._stats.size = len(array)
            self._stats.builds += 1

            if not array:
                self._root = None
                return None

            n = len(array)
            self._nodes = [None] * n

            # Create nodes
            for i in range(n):
                self._nodes[i] = CartesianNode(index=i, value=array[i])

            # Build using stack (O(n) algorithm)
            stack: List[CartesianNode[T]] = []

            for i in range(n):
                node = self._nodes[i]
                last_popped = None

                # Pop nodes with lower priority (greater value for min-heap)
                while stack and self._compare(node.value, stack[-1].value):
                    last_popped = stack.pop()

                if last_popped:
                    node.left = last_popped
                    last_popped.parent = node

                if stack:
                    stack[-1].right = node
                    node.parent = stack[-1]

                stack.append(node)

            # Root is the first element in stack
            self._root = stack[0] if stack else None

            # Calculate height
            self._stats.height = self._calculate_height(self._root)

            # Build RMQ structures
            self._build_rmq()

            logger.info(
                f"Cartesian tree built: {n} nodes, height {self._stats.height}"
            )

            return self._root

    def _calculate_height(self, node: Optional[CartesianNode[T]]) -> int:
        """Calculate tree height."""
        if not node:
            return 0
        return 1 + max(
            self._calculate_height(node.left),
            self._calculate_height(node.right)
        )

    def _build_rmq(self) -> None:
        """Build RMQ structures for O(1) queries."""
        if not self._root:
            return

        n = self._stats.size

        # Euler tour
        self._euler_tour = []
        self._first_occurrence = [-1] * n
        self._dfs_euler(self._root, 0)

        # Sparse table for range minimum on Euler tour
        m = len(self._euler_tour)

        # Log table
        self._log_table = [0] * (m + 1)
        for i in range(2, m + 1):
            self._log_table[i] = self._log_table[i // 2] + 1

        # Sparse table
        k = self._log_table[m] + 1
        self._sparse_table = [[0] * m for _ in range(k)]

        # Initialize with Euler tour indices
        for i in range(m):
            self._sparse_table[0][i] = i

        # Build sparse table
        for j in range(1, k):
            for i in range(m - (1 << j) + 1):
                left = self._sparse_table[j-1][i]
                right = self._sparse_table[j-1][i + (1 << (j-1))]

                if self._euler_tour[left] <= self._euler_tour[right]:
                    self._sparse_table[j][i] = left
                else:
                    self._sparse_table[j][i] = right

    def _dfs_euler(self, node: Optional[CartesianNode[T]], depth: int) -> None:
        """Build Euler tour and first occurrence."""
        if not node:
            return

        if self._first_occurrence[node.index] == -1:
            self._first_occurrence[node.index] = len(self._euler_tour)

        self._euler_tour.append(node.index)

        if node.left:
            self._dfs_euler(node.left, depth + 1)
            self._euler_tour.append(node.index)

        if node.right:
            self._dfs_euler(node.right, depth + 1)
            self._euler_tour.append(node.index)

    # ========================================================================
    # QUERIES
    # ========================================================================

    def rmq(self, left: int, right: int) -> int:
        """
        Range Minimum Query in O(1).

        Args:
            left: Left index
            right: Right index

        Returns:
            Index of minimum element in range
        """
        with self._lock:
            self._stats.queries += 1

            if left > right:
                left, right = right, left

            # Get range in Euler tour
            l = self._first_occurrence[left]
            r = self._first_occurrence[right]

            if l > r:
                l, r = r, l

            # Query sparse table
            length = r - l + 1
            k = self._log_table[length]

            left_val = self._sparse_table[k][l]
            right_val = self._sparse_table[k][r - (1 << k) + 1]

            if self._euler_tour[left_val] <= self._euler_tour[right_val]:
                return self._euler_tour[left_val]
            else:
                return self._euler_tour[right_val]

    def range_min(self, left: int, right: int) -> T:
        """
        Get minimum value in range.

        Args:
            left: Left index
            right: Right index

        Returns:
            Minimum value
        """
        idx = self.rmq(left, right)
        return self._array[idx]

    def lca(self, i: int, j: int) -> int:
        """
        Lowest Common Ancestor of indices i and j.

        Args:
            i: First index
            j: Second index

        Returns:
            Index of LCA
        """
        return self.rmq(i, j)

    # ========================================================================
    # TRAVERSAL
    # ========================================================================

    def inorder(self) -> List[Tuple[int, T]]:
        """
        In-order traversal (returns original array order).

        Returns:
            List of (index, value) pairs
        """
        result = []
        self._inorder_helper(self._root, result)
        return result

    def _inorder_helper(
        self,
        node: Optional[CartesianNode[T]],
        result: List[Tuple[int, T]]
    ) -> None:
        if not node:
            return
        self._inorder_helper(node.left, result)
        result.append((node.index, node.value))
        self._inorder_helper(node.right, result)

    def preorder(self) -> List[Tuple[int, T]]:
        """
        Pre-order traversal.

        Returns:
            List of (index, value) pairs
        """
        result = []
        self._preorder_helper(self._root, result)
        return result

    def _preorder_helper(
        self,
        node: Optional[CartesianNode[T]],
        result: List[Tuple[int, T]]
    ) -> None:
        if not node:
            return
        result.append((node.index, node.value))
        self._preorder_helper(node.left, result)
        self._preorder_helper(node.right, result)

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def get_root(self) -> Optional[CartesianNode[T]]:
        """Get root node."""
        return self._root

    def get_node(self, index: int) -> Optional[CartesianNode[T]]:
        """Get node by original array index."""
        if 0 <= index < len(self._nodes):
            return self._nodes[index]
        return None

    def __len__(self) -> int:
        return self._stats.size

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'size': self._stats.size,
            'height': self._stats.height,
            'builds': self._stats.builds,
            'queries': self._stats.queries
        }


# ============================================================================
# TREAP (CARTESIAN TREE WITH RANDOM PRIORITIES)
# ============================================================================

class ImplicitTreap(Generic[T]):
    """
    Implicit Treap - array with O(log n) operations.

    Features:
    - O(log n) insert/delete at any position
    - O(log n) range operations
    - O(log n) split/merge

    "Ba'el randomizes for balance." — Ba'el
    """

    @dataclass
    class Node(Generic[T]):
        value: T
        priority: float
        size: int = 1
        left: Optional['ImplicitTreap.Node[T]'] = None
        right: Optional['ImplicitTreap.Node[T]'] = None

    def __init__(self):
        """Initialize implicit treap."""
        import random
        self._root: Optional[ImplicitTreap.Node[T]] = None
        self._random = random.Random()
        self._lock = threading.RLock()

    def _get_size(self, node: Optional[Node[T]]) -> int:
        return node.size if node else 0

    def _update(self, node: Node[T]) -> None:
        if node:
            node.size = 1 + self._get_size(node.left) + self._get_size(node.right)

    def _split(
        self,
        node: Optional[Node[T]],
        key: int
    ) -> Tuple[Optional[Node[T]], Optional[Node[T]]]:
        """Split by implicit key (position)."""
        if not node:
            return None, None

        left_size = self._get_size(node.left)

        if left_size >= key:
            left, node.left = self._split(node.left, key)
            self._update(node)
            return left, node
        else:
            node.right, right = self._split(node.right, key - left_size - 1)
            self._update(node)
            return node, right

    def _merge(
        self,
        left: Optional[Node[T]],
        right: Optional[Node[T]]
    ) -> Optional[Node[T]]:
        """Merge two treaps."""
        if not left:
            return right
        if not right:
            return left

        if left.priority > right.priority:
            left.right = self._merge(left.right, right)
            self._update(left)
            return left
        else:
            right.left = self._merge(left, right.left)
            self._update(right)
            return right

    def insert(self, pos: int, value: T) -> None:
        """Insert value at position."""
        with self._lock:
            new_node = ImplicitTreap.Node(
                value=value,
                priority=self._random.random()
            )
            left, right = self._split(self._root, pos)
            self._root = self._merge(self._merge(left, new_node), right)

    def delete(self, pos: int) -> Optional[T]:
        """Delete and return value at position."""
        with self._lock:
            left, right = self._split(self._root, pos)
            deleted, right = self._split(right, 1)
            self._root = self._merge(left, right)
            return deleted.value if deleted else None

    def get(self, pos: int) -> Optional[T]:
        """Get value at position."""
        with self._lock:
            left, right = self._split(self._root, pos)
            value, new_right = self._split(right, 1)
            result = value.value if value else None
            self._root = self._merge(left, self._merge(value, new_right))
            return result

    def __len__(self) -> int:
        return self._get_size(self._root)

    def to_list(self) -> List[T]:
        """Convert to list."""
        result = []
        self._inorder(self._root, result)
        return result

    def _inorder(self, node: Optional[Node[T]], result: List[T]) -> None:
        if not node:
            return
        self._inorder(node.left, result)
        result.append(node.value)
        self._inorder(node.right, result)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_cartesian_tree() -> CartesianTreeEngine:
    """Create empty Cartesian tree."""
    return CartesianTreeEngine()


def build_cartesian_tree(array: List) -> CartesianTreeEngine:
    """
    Build Cartesian tree from array.

    Args:
        array: Input array

    Returns:
        Built Cartesian tree
    """
    tree = CartesianTreeEngine()
    tree.build(array)
    return tree


def rmq(array: List, left: int, right: int) -> int:
    """
    Range minimum query.

    Args:
        array: Input array
        left: Left index
        right: Right index

    Returns:
        Index of minimum
    """
    tree = build_cartesian_tree(array)
    return tree.rmq(left, right)


def create_implicit_treap() -> ImplicitTreap:
    """Create implicit treap."""
    return ImplicitTreap()
