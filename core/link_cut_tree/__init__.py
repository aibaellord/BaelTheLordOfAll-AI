"""
BAEL Link-Cut Tree Engine Implementation
========================================

Dynamic tree structure for path queries.

"Ba'el links and cuts between all realities." — Ba'el
"""

import logging
import threading
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.LinkCutTree")

T = TypeVar('T')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class LCTNode(Generic[T]):
    """Node in Link-Cut Tree."""
    id: int
    value: T
    parent: Optional['LCTNode[T]'] = None
    left: Optional['LCTNode[T]'] = None
    right: Optional['LCTNode[T]'] = None
    path_parent: Optional['LCTNode[T]'] = None  # For Splay tree forest
    reversed: bool = False  # Lazy reversal flag

    # Aggregates
    aggregate: Optional[T] = None  # Path aggregate
    size: int = 1


@dataclass
class LinkCutTreeStats:
    """Link-Cut tree statistics."""
    node_count: int = 0
    operations: int = 0
    access_count: int = 0


# ============================================================================
# LINK-CUT TREE ENGINE
# ============================================================================

class LinkCutTreeEngine(Generic[T]):
    """
    Link-Cut Tree for dynamic tree operations.

    Features:
    - O(log n) amortized link/cut
    - O(log n) amortized path queries
    - O(log n) LCA queries
    - Dynamic connectivity

    "Ba'el restructures the forest of possibilities." — Ba'el
    """

    def __init__(
        self,
        aggregate_fn: Optional[Callable[[T, T], T]] = None,
        identity: Optional[T] = None
    ):
        """
        Initialize Link-Cut Tree.

        Args:
            aggregate_fn: Function to aggregate path values
            identity: Identity element for aggregation
        """
        self._nodes: Dict[int, LCTNode[T]] = {}
        self._aggregate_fn = aggregate_fn
        self._identity = identity

        self._stats = LinkCutTreeStats()
        self._lock = threading.RLock()

        logger.info("Link-Cut tree initialized")

    # ========================================================================
    # SPLAY TREE OPERATIONS
    # ========================================================================

    def _push_down(self, node: LCTNode[T]) -> None:
        """Push lazy updates down."""
        if node.reversed:
            node.reversed = False
            node.left, node.right = node.right, node.left

            if node.left:
                node.left.reversed = not node.left.reversed
            if node.right:
                node.right.reversed = not node.right.reversed

    def _update(self, node: LCTNode[T]) -> None:
        """Update node aggregates."""
        left_size = node.left.size if node.left else 0
        right_size = node.right.size if node.right else 0
        node.size = 1 + left_size + right_size

        if self._aggregate_fn:
            node.aggregate = node.value

            if node.left and node.left.aggregate is not None:
                node.aggregate = self._aggregate_fn(node.left.aggregate, node.aggregate)
            if node.right and node.right.aggregate is not None:
                node.aggregate = self._aggregate_fn(node.aggregate, node.right.aggregate)

    def _is_root(self, node: LCTNode[T]) -> bool:
        """Check if node is root of its splay tree."""
        if not node.parent:
            return True
        return node.parent.left != node and node.parent.right != node

    def _rotate(self, node: LCTNode[T]) -> None:
        """Rotate node with its parent."""
        parent = node.parent
        grandparent = parent.parent

        if grandparent:
            if grandparent.left == parent:
                grandparent.left = node
            elif grandparent.right == parent:
                grandparent.right = node

        if parent.left == node:
            parent.left = node.right
            if node.right:
                node.right.parent = parent
            node.right = parent
        else:
            parent.right = node.left
            if node.left:
                node.left.parent = parent
            node.left = parent

        node.parent = grandparent
        parent.parent = node

        if node.path_parent is None:
            node.path_parent = parent.path_parent
        parent.path_parent = None

        self._update(parent)
        self._update(node)

    def _splay(self, node: LCTNode[T]) -> None:
        """Splay node to root of its splay tree."""
        # Push down from root to node
        path = []
        current = node

        while not self._is_root(current):
            path.append(current.parent)
            current = current.parent

        path.reverse()

        for ancestor in path:
            self._push_down(ancestor)
        self._push_down(node)

        # Splay
        while not self._is_root(node):
            parent = node.parent

            if self._is_root(parent):
                self._rotate(node)
            elif (parent.left == node) == (parent.parent.left == parent):
                # Zig-zig
                self._rotate(parent)
                self._rotate(node)
            else:
                # Zig-zag
                self._rotate(node)
                self._rotate(node)

    # ========================================================================
    # CORE OPERATIONS
    # ========================================================================

    def _access(self, node: LCTNode[T]) -> None:
        """
        Make path from root to node preferred.

        After access, node is root of aux tree representing
        the path from original root to this node.
        """
        self._stats.access_count += 1

        self._splay(node)

        # Cut right child (it's no longer on preferred path)
        if node.right:
            node.right.path_parent = node
            node.right.parent = None
            node.right = None
            self._update(node)

        # Walk up and connect
        while node.path_parent:
            parent = node.path_parent
            self._splay(parent)

            # Cut parent's right child
            if parent.right:
                parent.right.path_parent = parent
                parent.right.parent = None

            # Attach node as right child
            parent.right = node
            node.parent = parent
            node.path_parent = None

            self._update(parent)
            self._splay(node)

        self._stats.operations += 1

    def make_root(self, node_id: int) -> None:
        """
        Make node the root of its tree.

        Args:
            node_id: Node to make root
        """
        with self._lock:
            node = self._nodes.get(node_id)
            if not node:
                return

            self._access(node)
            node.reversed = not node.reversed
            self._push_down(node)

    def find_root(self, node_id: int) -> Optional[int]:
        """
        Find root of tree containing node.

        Args:
            node_id: Node to find root for

        Returns:
            Root node ID
        """
        with self._lock:
            node = self._nodes.get(node_id)
            if not node:
                return None

            self._access(node)

            # Root is leftmost node in aux tree
            while node.left:
                self._push_down(node)
                node = node.left

            self._splay(node)
            return node.id

    def link(self, child_id: int, parent_id: int) -> bool:
        """
        Link child to parent (child becomes child of parent).

        Args:
            child_id: Child node (must be root of its tree)
            parent_id: Parent node

        Returns:
            True if successful
        """
        with self._lock:
            child = self._nodes.get(child_id)
            parent = self._nodes.get(parent_id)

            if not child or not parent:
                return False

            # Make child root of its tree
            self.make_root(child_id)

            # Access parent
            self._access(parent)

            # Link
            child.path_parent = parent

            self._stats.operations += 1
            return True

    def cut(self, node_id: int) -> bool:
        """
        Cut edge between node and its parent.

        Args:
            node_id: Node to cut from parent

        Returns:
            True if successful
        """
        with self._lock:
            node = self._nodes.get(node_id)
            if not node:
                return False

            self._access(node)

            if node.left:
                node.left.parent = None
                node.left = None
                self._update(node)

            self._stats.operations += 1
            return True

    def cut_edge(self, u_id: int, v_id: int) -> bool:
        """
        Cut edge between two nodes.

        Args:
            u_id: First node
            v_id: Second node

        Returns:
            True if successful
        """
        with self._lock:
            u = self._nodes.get(u_id)
            v = self._nodes.get(v_id)

            if not u or not v:
                return False

            self.make_root(u_id)
            self._access(v)

            if v.left != u or u.right:
                return False  # Edge doesn't exist

            v.left = None
            u.parent = None
            self._update(v)

            self._stats.operations += 1
            return True

    # ========================================================================
    # NODE MANAGEMENT
    # ========================================================================

    def add_node(self, node_id: int, value: T) -> None:
        """
        Add a new node.

        Args:
            node_id: Node identifier
            value: Node value
        """
        with self._lock:
            if node_id in self._nodes:
                self._nodes[node_id].value = value
                return

            node = LCTNode(id=node_id, value=value)
            node.aggregate = value
            self._nodes[node_id] = node
            self._stats.node_count += 1

    def get_value(self, node_id: int) -> Optional[T]:
        """Get node value."""
        with self._lock:
            node = self._nodes.get(node_id)
            return node.value if node else None

    def set_value(self, node_id: int, value: T) -> None:
        """Set node value."""
        with self._lock:
            node = self._nodes.get(node_id)
            if node:
                node.value = value
                self._splay(node)
                self._update(node)

    # ========================================================================
    # QUERIES
    # ========================================================================

    def connected(self, u_id: int, v_id: int) -> bool:
        """
        Check if two nodes are connected.

        Args:
            u_id: First node
            v_id: Second node

        Returns:
            True if connected
        """
        with self._lock:
            u_root = self.find_root(u_id)
            v_root = self.find_root(v_id)

            return u_root is not None and u_root == v_root

    def lca(self, u_id: int, v_id: int) -> Optional[int]:
        """
        Find lowest common ancestor.

        Args:
            u_id: First node
            v_id: Second node

        Returns:
            LCA node ID or None
        """
        with self._lock:
            u = self._nodes.get(u_id)
            v = self._nodes.get(v_id)

            if not u or not v:
                return None

            self._access(u)
            self._access(v)

            if u.path_parent:
                return u.path_parent.id

            return u.id

    def path_aggregate(self, u_id: int, v_id: int) -> Optional[T]:
        """
        Get aggregate of path between two nodes.

        Args:
            u_id: First node
            v_id: Second node

        Returns:
            Path aggregate
        """
        if not self._aggregate_fn:
            return None

        with self._lock:
            u = self._nodes.get(u_id)
            v = self._nodes.get(v_id)

            if not u or not v:
                return None

            self.make_root(u_id)
            self._access(v)

            return v.aggregate

    def path_length(self, u_id: int, v_id: int) -> int:
        """
        Get length of path (number of edges) between nodes.

        Args:
            u_id: First node
            v_id: Second node

        Returns:
            Path length or -1 if not connected
        """
        with self._lock:
            u = self._nodes.get(u_id)
            v = self._nodes.get(v_id)

            if not u or not v:
                return -1

            if not self.connected(u_id, v_id):
                return -1

            self.make_root(u_id)
            self._access(v)

            return v.size - 1

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def __len__(self) -> int:
        return self._stats.node_count

    def __contains__(self, node_id: int) -> bool:
        return node_id in self._nodes

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'node_count': self._stats.node_count,
            'operations': self._stats.operations,
            'access_count': self._stats.access_count
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_link_cut_tree(
    aggregate_fn: Optional[Callable[[T, T], T]] = None,
    identity: Optional[T] = None
) -> LinkCutTreeEngine[T]:
    """Create Link-Cut tree."""
    return LinkCutTreeEngine(aggregate_fn, identity)


def create_sum_link_cut_tree() -> LinkCutTreeEngine[int]:
    """Create Link-Cut tree for path sum queries."""
    return LinkCutTreeEngine(lambda a, b: a + b, 0)


def create_max_link_cut_tree() -> LinkCutTreeEngine[int]:
    """Create Link-Cut tree for path max queries."""
    return LinkCutTreeEngine(max, float('-inf'))


def create_min_link_cut_tree() -> LinkCutTreeEngine[int]:
    """Create Link-Cut tree for path min queries."""
    return LinkCutTreeEngine(min, float('inf'))
