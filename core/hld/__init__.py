"""
BAEL Heavy-Light Decomposition Engine
=====================================

Decompose tree for efficient path queries.

"Ba'el carves reality into heavy and light paths." — Ba'el
"""

import logging
import threading
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.HLDecomposition")

T = TypeVar('T')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class HLDNode:
    """Node in Heavy-Light Decomposition."""
    id: int
    parent: int = -1
    depth: int = 0
    subtree_size: int = 1
    chain_head: int = -1  # Head of heavy chain
    chain_position: int = -1  # Position in decomposition
    heavy_child: int = -1  # Heavy child


@dataclass
class HLDStats:
    """HLD statistics."""
    node_count: int = 0
    chain_count: int = 0
    queries: int = 0
    updates: int = 0


# ============================================================================
# HEAVY-LIGHT DECOMPOSITION ENGINE
# ============================================================================

class HLDecompositionEngine(Generic[T]):
    """
    Heavy-Light Decomposition for efficient tree path queries.

    Features:
    - O(n) preprocessing
    - O(log^2 n) path queries with segment tree
    - O(log n) LCA queries
    - Path update and query operations

    "Ba'el decomposes the tree of reality." — Ba'el
    """

    def __init__(self):
        """Initialize HLD engine."""
        self._nodes: Dict[int, HLDNode] = {}
        self._adjacency: Dict[int, List[int]] = {}
        self._decomposition: List[int] = []  # Nodes in decomposition order
        self._values: Dict[int, T] = {}
        self._segment_tree: List[T] = []
        self._combine: Callable[[T, T], T] = lambda a, b: a
        self._identity: T = None
        self._stats = HLDStats()
        self._lock = threading.RLock()
        self._built = False

        logger.debug("HLD engine initialized")

    # ========================================================================
    # TREE CONSTRUCTION
    # ========================================================================

    def add_node(self, node_id: int, value: T = None) -> None:
        """
        Add a node.

        Args:
            node_id: Node ID
            value: Node value
        """
        with self._lock:
            if node_id not in self._nodes:
                self._nodes[node_id] = HLDNode(id=node_id)
                self._adjacency[node_id] = []
                self._values[node_id] = value
                self._stats.node_count += 1
                self._built = False

    def add_edge(self, u: int, v: int) -> None:
        """
        Add undirected edge.

        Args:
            u: First node
            v: Second node
        """
        with self._lock:
            self.add_node(u)
            self.add_node(v)

            self._adjacency[u].append(v)
            self._adjacency[v].append(u)
            self._built = False

    def set_value(self, node_id: int, value: T) -> None:
        """Set node value."""
        with self._lock:
            if node_id in self._nodes:
                self._values[node_id] = value

                if self._built:
                    pos = self._nodes[node_id].chain_position
                    self._update_segment_tree(pos, value)

    # ========================================================================
    # BUILD DECOMPOSITION
    # ========================================================================

    def build(
        self,
        root: int = 0,
        combine: Callable[[T, T], T] = None,
        identity: T = None
    ) -> None:
        """
        Build Heavy-Light Decomposition.

        Args:
            root: Root node
            combine: Function to combine values
            identity: Identity value for combine
        """
        with self._lock:
            if root not in self._nodes:
                raise ValueError(f"Root {root} not found")

            self._combine = combine or (lambda a, b: a)
            self._identity = identity

            # DFS 1: Compute subtree sizes and find heavy children
            self._dfs_size(root, -1)

            # DFS 2: Decompose into chains
            self._decomposition = []
            self._dfs_decompose(root, -1, root)

            # Count chains
            chain_heads = set(node.chain_head for node in self._nodes.values())
            self._stats.chain_count = len(chain_heads)

            # Build segment tree
            self._build_segment_tree()

            self._built = True
            logger.info(f"HLD built: {self._stats.node_count} nodes, {self._stats.chain_count} chains")

    def _dfs_size(self, node: int, parent: int) -> int:
        """DFS to compute subtree sizes."""
        node_data = self._nodes[node]
        node_data.parent = parent
        node_data.depth = self._nodes[parent].depth + 1 if parent != -1 else 0
        node_data.subtree_size = 1

        max_child_size = 0

        for child in self._adjacency[node]:
            if child != parent:
                child_size = self._dfs_size(child, node)
                node_data.subtree_size += child_size

                if child_size > max_child_size:
                    max_child_size = child_size
                    node_data.heavy_child = child

        return node_data.subtree_size

    def _dfs_decompose(self, node: int, parent: int, chain_head: int) -> None:
        """DFS to decompose into chains."""
        node_data = self._nodes[node]
        node_data.chain_head = chain_head
        node_data.chain_position = len(self._decomposition)

        self._decomposition.append(node)

        # Process heavy child first
        if node_data.heavy_child != -1:
            self._dfs_decompose(node_data.heavy_child, node, chain_head)

        # Process light children
        for child in self._adjacency[node]:
            if child != parent and child != node_data.heavy_child:
                self._dfs_decompose(child, node, child)

    # ========================================================================
    # SEGMENT TREE
    # ========================================================================

    def _build_segment_tree(self) -> None:
        """Build segment tree over decomposition."""
        n = len(self._decomposition)
        self._segment_tree = [self._identity] * (4 * n)

        if n > 0:
            self._build_st(1, 0, n - 1)

    def _build_st(self, idx: int, left: int, right: int) -> None:
        """Build segment tree recursively."""
        if left == right:
            node = self._decomposition[left]
            self._segment_tree[idx] = self._values.get(node, self._identity)
            return

        mid = (left + right) // 2
        self._build_st(2 * idx, left, mid)
        self._build_st(2 * idx + 1, mid + 1, right)

        self._segment_tree[idx] = self._combine(
            self._segment_tree[2 * idx],
            self._segment_tree[2 * idx + 1]
        )

    def _query_st(self, idx: int, left: int, right: int, ql: int, qr: int) -> T:
        """Query segment tree."""
        if qr < left or ql > right:
            return self._identity

        if ql <= left and right <= qr:
            return self._segment_tree[idx]

        mid = (left + right) // 2
        left_result = self._query_st(2 * idx, left, mid, ql, qr)
        right_result = self._query_st(2 * idx + 1, mid + 1, right, ql, qr)

        return self._combine(left_result, right_result)

    def _update_segment_tree(self, pos: int, value: T) -> None:
        """Update segment tree at position."""
        n = len(self._decomposition)
        self._update_st(1, 0, n - 1, pos, value)

    def _update_st(
        self,
        idx: int,
        left: int,
        right: int,
        pos: int,
        value: T
    ) -> None:
        """Update segment tree recursively."""
        if left == right:
            self._segment_tree[idx] = value
            return

        mid = (left + right) // 2

        if pos <= mid:
            self._update_st(2 * idx, left, mid, pos, value)
        else:
            self._update_st(2 * idx + 1, mid + 1, right, pos, value)

        self._segment_tree[idx] = self._combine(
            self._segment_tree[2 * idx],
            self._segment_tree[2 * idx + 1]
        )

    # ========================================================================
    # PATH QUERIES
    # ========================================================================

    def path_query(self, u: int, v: int) -> T:
        """
        Query on path from u to v.

        Args:
            u: First endpoint
            v: Second endpoint

        Returns:
            Combined value on path
        """
        with self._lock:
            if not self._built:
                raise RuntimeError("Must build before querying")

            self._stats.queries += 1

            result = self._identity
            n = len(self._decomposition)

            while self._nodes[u].chain_head != self._nodes[v].chain_head:
                # Move the deeper chain head up
                if self._nodes[self._nodes[u].chain_head].depth < \
                   self._nodes[self._nodes[v].chain_head].depth:
                    u, v = v, u

                # Query from u to its chain head
                chain_head = self._nodes[u].chain_head
                head_pos = self._nodes[chain_head].chain_position
                u_pos = self._nodes[u].chain_position

                segment_result = self._query_st(1, 0, n - 1, head_pos, u_pos)
                result = self._combine(result, segment_result)

                # Move to parent of chain head
                u = self._nodes[chain_head].parent

            # u and v are now on same chain
            u_pos = self._nodes[u].chain_position
            v_pos = self._nodes[v].chain_position

            if u_pos > v_pos:
                u_pos, v_pos = v_pos, u_pos

            segment_result = self._query_st(1, 0, n - 1, u_pos, v_pos)
            result = self._combine(result, segment_result)

            return result

    def lca(self, u: int, v: int) -> int:
        """
        Find Lowest Common Ancestor.

        Args:
            u: First node
            v: Second node

        Returns:
            LCA node
        """
        with self._lock:
            if not self._built:
                raise RuntimeError("Must build before LCA query")

            while self._nodes[u].chain_head != self._nodes[v].chain_head:
                if self._nodes[self._nodes[u].chain_head].depth < \
                   self._nodes[self._nodes[v].chain_head].depth:
                    u, v = v, u

                u = self._nodes[self._nodes[u].chain_head].parent

            # Return the one with smaller depth
            if self._nodes[u].depth < self._nodes[v].depth:
                return u
            return v

    def path_length(self, u: int, v: int) -> int:
        """
        Get path length (number of edges).

        Args:
            u: First node
            v: Second node

        Returns:
            Number of edges on path
        """
        with self._lock:
            if not self._built:
                raise RuntimeError("Must build first")

            lca_node = self.lca(u, v)
            return (self._nodes[u].depth + self._nodes[v].depth -
                    2 * self._nodes[lca_node].depth)

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def get_depth(self, node: int) -> int:
        """Get node depth."""
        return self._nodes[node].depth if node in self._nodes else -1

    def get_parent(self, node: int) -> int:
        """Get node parent."""
        return self._nodes[node].parent if node in self._nodes else -1

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'node_count': self._stats.node_count,
            'chain_count': self._stats.chain_count,
            'queries': self._stats.queries,
            'updates': self._stats.updates
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_hld() -> HLDecompositionEngine:
    """Create HLD engine."""
    return HLDecompositionEngine()


def build_hld_from_edges(
    edges: List[Tuple[int, int]],
    root: int = 0
) -> HLDecompositionEngine:
    """
    Build HLD from edge list.

    Args:
        edges: List of (u, v) edges
        root: Root node

    Returns:
        Built HLD engine
    """
    hld = HLDecompositionEngine()

    for u, v in edges:
        hld.add_edge(u, v)

    hld.build(root)
    return hld


def build_sum_hld(
    edges: List[Tuple[int, int]],
    values: Dict[int, int],
    root: int = 0
) -> HLDecompositionEngine[int]:
    """
    Build HLD with sum queries.

    Args:
        edges: Edge list
        values: Node values
        root: Root node

    Returns:
        HLD engine for sum queries
    """
    hld = HLDecompositionEngine[int]()

    for u, v in edges:
        hld.add_edge(u, v)

    for node, value in values.items():
        hld.set_value(node, value)

    hld.build(root, combine=lambda a, b: (a or 0) + (b or 0), identity=0)
    return hld
