"""
BAEL Persistent Segment Tree Engine
====================================

Immutable segment tree with version history.

"Ba'el preserves all states across time." — Ba'el
"""

import logging
import threading
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar
from dataclasses import dataclass

logger = logging.getLogger("BAEL.PersistentSegmentTree")

T = TypeVar('T')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class PSTNode(Generic[T]):
    """Persistent segment tree node."""
    value: T
    left: Optional['PSTNode[T]'] = None
    right: Optional['PSTNode[T]'] = None


@dataclass
class PSTStats:
    """Persistent segment tree statistics."""
    size: int = 0
    versions: int = 0
    nodes_created: int = 0
    queries: int = 0
    updates: int = 0


# ============================================================================
# PERSISTENT SEGMENT TREE ENGINE
# ============================================================================

class PersistentSegmentTreeEngine(Generic[T]):
    """
    Persistent Segment Tree with version history.

    Features:
    - O(n) initial build
    - O(log n) point update (creates new version)
    - O(log n) range query
    - O(log n) space per update
    - Access any historical version

    "Ba'el remembers all versions of reality." — Ba'el
    """

    def __init__(
        self,
        combine: Callable[[T, T], T],
        identity: T
    ):
        """
        Initialize persistent segment tree.

        Args:
            combine: Function to combine two values
            identity: Identity element
        """
        self._combine = combine
        self._identity = identity
        self._roots: List[Optional[PSTNode[T]]] = []
        self._size = 0
        self._stats = PSTStats()
        self._lock = threading.RLock()

        logger.debug("Persistent segment tree initialized")

    # ========================================================================
    # BUILD
    # ========================================================================

    def build(self, array: List[T]) -> int:
        """
        Build initial tree from array.

        Args:
            array: Input array

        Returns:
            Version number (0)
        """
        with self._lock:
            self._size = len(array)
            self._stats.size = len(array)

            if not array:
                self._roots = [None]
                self._stats.versions = 1
                return 0

            root = self._build(array, 0, len(array) - 1)
            self._roots = [root]
            self._stats.versions = 1

            logger.info(f"PST built: {len(array)} elements, version 0")

            return 0

    def _build(self, array: List[T], left: int, right: int) -> PSTNode[T]:
        """Build tree recursively."""
        self._stats.nodes_created += 1

        if left == right:
            return PSTNode(value=array[left])

        mid = (left + right) // 2
        left_child = self._build(array, left, mid)
        right_child = self._build(array, mid + 1, right)

        return PSTNode(
            value=self._combine(left_child.value, right_child.value),
            left=left_child,
            right=right_child
        )

    # ========================================================================
    # UPDATE
    # ========================================================================

    def update(self, index: int, value: T, version: int = -1) -> int:
        """
        Update element and create new version.

        Args:
            index: Index to update
            value: New value
            version: Base version (-1 for latest)

        Returns:
            New version number
        """
        with self._lock:
            self._stats.updates += 1

            if version < 0:
                version = len(self._roots) - 1

            if version >= len(self._roots):
                raise IndexError(f"Version {version} does not exist")

            old_root = self._roots[version]
            new_root = self._update(old_root, 0, self._size - 1, index, value)

            self._roots.append(new_root)
            self._stats.versions += 1

            new_version = len(self._roots) - 1
            logger.debug(f"PST update: index {index}, new version {new_version}")

            return new_version

    def _update(
        self,
        node: Optional[PSTNode[T]],
        node_left: int,
        node_right: int,
        index: int,
        value: T
    ) -> PSTNode[T]:
        """Update and create new nodes on path."""
        self._stats.nodes_created += 1

        if node_left == node_right:
            return PSTNode(value=value)

        mid = (node_left + node_right) // 2

        if index <= mid:
            # Update left child
            new_left = self._update(
                node.left if node else None,
                node_left, mid, index, value
            )
            new_right = node.right if node else None
        else:
            # Update right child
            new_left = node.left if node else None
            new_right = self._update(
                node.right if node else None,
                mid + 1, node_right, index, value
            )

        left_val = new_left.value if new_left else self._identity
        right_val = new_right.value if new_right else self._identity

        return PSTNode(
            value=self._combine(left_val, right_val),
            left=new_left,
            right=new_right
        )

    # ========================================================================
    # QUERY
    # ========================================================================

    def query(self, left: int, right: int, version: int = -1) -> T:
        """
        Range query on specific version.

        Args:
            left: Left index
            right: Right index
            version: Version to query (-1 for latest)

        Returns:
            Combined value
        """
        with self._lock:
            self._stats.queries += 1

            if version < 0:
                version = len(self._roots) - 1

            if version >= len(self._roots):
                raise IndexError(f"Version {version} does not exist")

            return self._query(self._roots[version], 0, self._size - 1, left, right)

    def _query(
        self,
        node: Optional[PSTNode[T]],
        node_left: int,
        node_right: int,
        query_left: int,
        query_right: int
    ) -> T:
        """Query recursively."""
        if not node or query_left > node_right or query_right < node_left:
            return self._identity

        if query_left <= node_left and node_right <= query_right:
            return node.value

        mid = (node_left + node_right) // 2

        left_val = self._query(node.left, node_left, mid, query_left, query_right)
        right_val = self._query(node.right, mid + 1, node_right, query_left, query_right)

        return self._combine(left_val, right_val)

    def get(self, index: int, version: int = -1) -> T:
        """Get single element at index."""
        return self.query(index, index, version)

    # ========================================================================
    # VERSION MANAGEMENT
    # ========================================================================

    def version_count(self) -> int:
        """Get number of versions."""
        return len(self._roots)

    def latest_version(self) -> int:
        """Get latest version number."""
        return len(self._roots) - 1

    def copy_version(self, version: int) -> int:
        """
        Create copy of a version (fork).

        Args:
            version: Version to copy

        Returns:
            New version number
        """
        with self._lock:
            if version >= len(self._roots):
                raise IndexError(f"Version {version} does not exist")

            self._roots.append(self._roots[version])
            self._stats.versions += 1

            return len(self._roots) - 1

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def to_list(self, version: int = -1) -> List[T]:
        """Convert version to list."""
        with self._lock:
            return [self.get(i, version) for i in range(self._size)]

    def __len__(self) -> int:
        return self._size

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'size': self._stats.size,
            'versions': self._stats.versions,
            'nodes_created': self._stats.nodes_created,
            'queries': self._stats.queries,
            'updates': self._stats.updates,
            'avg_nodes_per_version': self._stats.nodes_created / max(1, self._stats.versions)
        }


# ============================================================================
# SPECIALIZED VARIANTS
# ============================================================================

class PersistentSumTree(PersistentSegmentTreeEngine[int]):
    """Persistent segment tree for range sums."""

    def __init__(self):
        super().__init__(combine=lambda a, b: a + b, identity=0)


class PersistentMinTree(PersistentSegmentTreeEngine):
    """Persistent segment tree for range minimum."""

    def __init__(self):
        super().__init__(
            combine=lambda a, b: min(a, b) if a != float('inf') and b != float('inf')
                                 else a if b == float('inf') else b,
            identity=float('inf')
        )


class PersistentMaxTree(PersistentSegmentTreeEngine):
    """Persistent segment tree for range maximum."""

    def __init__(self):
        super().__init__(
            combine=lambda a, b: max(a, b) if a != float('-inf') and b != float('-inf')
                                 else a if b == float('-inf') else b,
            identity=float('-inf')
        )


# ============================================================================
# KTH ELEMENT QUERIES
# ============================================================================

class PersistentKthTree:
    """
    Persistent segment tree for kth element queries.

    Can answer: kth smallest in range after sequence of updates.

    "Ba'el finds the kth element across all timelines." — Ba'el
    """

    def __init__(self, max_value: int = 10**5):
        """
        Initialize kth element tree.

        Args:
            max_value: Maximum value in array
        """
        self._max_value = max_value
        self._roots: List[Optional[PSTNode[int]]] = []
        self._size = 0
        self._lock = threading.RLock()

    @dataclass
    class Node:
        count: int = 0
        left: Optional['PersistentKthTree.Node'] = None
        right: Optional['PersistentKthTree.Node'] = None

    def build(self, array: List[int]) -> None:
        """Build from sorted array of values."""
        with self._lock:
            self._size = len(array)

            # Build empty tree
            self._roots = [self._build_empty(0, self._max_value)]

            # Insert elements one by one
            for val in array:
                new_root = self._insert(self._roots[-1], 0, self._max_value, val)
                self._roots.append(new_root)

    def _build_empty(self, left: int, right: int) -> 'PersistentKthTree.Node':
        return PersistentKthTree.Node()

    def _insert(
        self,
        node: Optional['PersistentKthTree.Node'],
        left: int,
        right: int,
        value: int
    ) -> 'PersistentKthTree.Node':
        """Insert value and create new nodes."""
        new_node = PersistentKthTree.Node(
            count=(node.count if node else 0) + 1
        )

        if left == right:
            return new_node

        mid = (left + right) // 2

        if value <= mid:
            new_node.left = self._insert(
                node.left if node else None,
                left, mid, value
            )
            new_node.right = node.right if node else None
        else:
            new_node.left = node.left if node else None
            new_node.right = self._insert(
                node.right if node else None,
                mid + 1, right, value
            )

        return new_node

    def kth_element(self, left_idx: int, right_idx: int, k: int) -> int:
        """
        Find kth smallest in original array range [left_idx, right_idx].

        Args:
            left_idx: Left index in original array
            right_idx: Right index in original array
            k: Kth element (1-indexed)

        Returns:
            Kth smallest value
        """
        with self._lock:
            left_tree = self._roots[left_idx]
            right_tree = self._roots[right_idx + 1]

            return self._kth(left_tree, right_tree, 0, self._max_value, k)

    def _kth(
        self,
        left_node: Optional['PersistentKthTree.Node'],
        right_node: Optional['PersistentKthTree.Node'],
        left: int,
        right: int,
        k: int
    ) -> int:
        """Find kth element recursively."""
        if left == right:
            return left

        mid = (left + right) // 2

        left_count = (
            (right_node.left.count if right_node and right_node.left else 0) -
            (left_node.left.count if left_node and left_node.left else 0)
        )

        if k <= left_count:
            return self._kth(
                left_node.left if left_node else None,
                right_node.left if right_node else None,
                left, mid, k
            )
        else:
            return self._kth(
                left_node.right if left_node else None,
                right_node.right if right_node else None,
                mid + 1, right, k - left_count
            )


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_persistent_segment_tree(
    combine: Callable = lambda a, b: a + b,
    identity: Any = 0
) -> PersistentSegmentTreeEngine:
    """Create persistent segment tree."""
    return PersistentSegmentTreeEngine(combine, identity)


def create_persistent_sum_tree() -> PersistentSumTree:
    """Create persistent sum tree."""
    return PersistentSumTree()


def create_persistent_min_tree() -> PersistentMinTree:
    """Create persistent min tree."""
    return PersistentMinTree()


def create_persistent_max_tree() -> PersistentMaxTree:
    """Create persistent max tree."""
    return PersistentMaxTree()


def build_persistent_sum_tree(array: List[int]) -> PersistentSumTree:
    """Build persistent sum tree from array."""
    tree = PersistentSumTree()
    tree.build(array)
    return tree
