"""
BAEL Heavy-Light Decomposition Engine
=====================================

Tree path queries in O(log² n) via HLD.

"Ba'el decomposes trees heavily and lightly." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple, Callable, Generic, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger("BAEL.HeavyLightDecomposition")


T = TypeVar('T')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class HLDInfo:
    """Heavy-Light Decomposition information."""
    parent: List[int]
    depth: List[int]
    heavy: List[int]      # Heavy child of each node
    head: List[int]       # Head of chain containing node
    position: List[int]   # Position in segment tree
    size: List[int]       # Subtree size


class SegmentTree(Generic[T]):
    """
    Segment tree for HLD queries.

    "Ba'el segments for efficiency." — Ba'el
    """

    def __init__(
        self,
        size: int,
        identity: T,
        combine: Callable[[T, T], T]
    ):
        """Initialize segment tree."""
        self._n = size
        self._identity = identity
        self._combine = combine
        self._tree = [identity] * (4 * size)
        self._lazy = [None] * (4 * size)

    def build(self, values: List[T]):
        """Build segment tree from values."""
        self._build(1, 0, self._n - 1, values)

    def _build(self, node: int, start: int, end: int, values: List[T]):
        if start == end:
            if start < len(values):
                self._tree[node] = values[start]
            return

        mid = (start + end) // 2
        self._build(2 * node, start, mid, values)
        self._build(2 * node + 1, mid + 1, end, values)
        self._tree[node] = self._combine(self._tree[2 * node], self._tree[2 * node + 1])

    def update(self, idx: int, value: T):
        """Point update."""
        self._update(1, 0, self._n - 1, idx, value)

    def _update(self, node: int, start: int, end: int, idx: int, value: T):
        if start == end:
            self._tree[node] = value
            return

        mid = (start + end) // 2
        if idx <= mid:
            self._update(2 * node, start, mid, idx, value)
        else:
            self._update(2 * node + 1, mid + 1, end, idx, value)

        self._tree[node] = self._combine(self._tree[2 * node], self._tree[2 * node + 1])

    def query(self, left: int, right: int) -> T:
        """Range query."""
        return self._query(1, 0, self._n - 1, left, right)

    def _query(self, node: int, start: int, end: int, left: int, right: int) -> T:
        if right < start or left > end:
            return self._identity

        if left <= start and end <= right:
            return self._tree[node]

        mid = (start + end) // 2
        left_result = self._query(2 * node, start, mid, left, right)
        right_result = self._query(2 * node + 1, mid + 1, end, left, right)

        return self._combine(left_result, right_result)


# ============================================================================
# HEAVY-LIGHT DECOMPOSITION
# ============================================================================

class HeavyLightDecomposition:
    """
    Heavy-Light Decomposition for tree path queries.

    Features:
    - O(n) preprocessing
    - O(log² n) path queries
    - O(log n) point updates
    - Supports any associative operation

    "Ba'el queries paths in logarithmic time." — Ba'el
    """

    def __init__(
        self,
        n: int,
        edges: List[Tuple[int, int]],
        root: int = 0,
        values: Optional[List[int]] = None,
        combine: Callable[[int, int], int] = lambda a, b: a + b,
        identity: int = 0
    ):
        """
        Initialize HLD.

        Args:
            n: Number of nodes
            edges: Tree edges (undirected)
            root: Root node
            values: Node values
            combine: Associative combine function
            identity: Identity element for combine
        """
        self._n = n
        self._root = root
        self._combine = combine
        self._identity = identity
        self._lock = threading.RLock()

        # Build adjacency list
        self._adj: List[List[int]] = [[] for _ in range(n)]
        for u, v in edges:
            self._adj[u].append(v)
            self._adj[v].append(u)

        # Initialize HLD arrays
        self._parent = [-1] * n
        self._depth = [0] * n
        self._heavy = [-1] * n
        self._head = list(range(n))  # Initially each node is its own chain head
        self._position = [0] * n
        self._size = [1] * n

        # Values for segment tree
        self._values = values if values else [0] * n
        self._pos_to_node = [0] * n

        # Build HLD
        self._current_pos = 0
        self._dfs_size(root, -1)
        self._dfs_hld(root, -1, root)

        # Build segment tree with reordered values
        ordered_values = [self._values[self._pos_to_node[i]] for i in range(n)]
        self._segment_tree = SegmentTree(n, identity, combine)
        self._segment_tree.build(ordered_values)

    def _dfs_size(self, u: int, parent: int):
        """First DFS: compute sizes and find heavy children."""
        self._parent[u] = parent
        self._depth[u] = self._depth[parent] + 1 if parent >= 0 else 0

        max_child_size = 0

        for v in self._adj[u]:
            if v != parent:
                self._dfs_size(v, u)
                self._size[u] += self._size[v]

                if self._size[v] > max_child_size:
                    max_child_size = self._size[v]
                    self._heavy[u] = v

    def _dfs_hld(self, u: int, parent: int, head: int):
        """Second DFS: assign positions and chain heads."""
        self._head[u] = head
        self._position[u] = self._current_pos
        self._pos_to_node[self._current_pos] = u
        self._current_pos += 1

        # Process heavy child first (keeps chain contiguous)
        if self._heavy[u] != -1:
            self._dfs_hld(self._heavy[u], u, head)

        # Process light children
        for v in self._adj[u]:
            if v != parent and v != self._heavy[u]:
                self._dfs_hld(v, u, v)  # New chain starts at v

    def query_path(self, u: int, v: int) -> int:
        """
        Query on path from u to v.

        Returns combined value using combine function.
        """
        with self._lock:
            result = self._identity

            while self._head[u] != self._head[v]:
                # Move deeper node up its chain
                if self._depth[self._head[u]] < self._depth[self._head[v]]:
                    u, v = v, u

                # Query segment from head to u
                left = self._position[self._head[u]]
                right = self._position[u]
                result = self._combine(result, self._segment_tree.query(left, right))

                # Move to parent of chain head
                u = self._parent[self._head[u]]

            # Now u and v are in same chain
            if self._depth[u] > self._depth[v]:
                u, v = v, u

            left = self._position[u]
            right = self._position[v]
            result = self._combine(result, self._segment_tree.query(left, right))

            return result

    def update(self, node: int, value: int):
        """
        Update value at node.
        """
        with self._lock:
            self._values[node] = value
            self._segment_tree.update(self._position[node], value)

    def lca(self, u: int, v: int) -> int:
        """
        Find lowest common ancestor of u and v.
        """
        with self._lock:
            while self._head[u] != self._head[v]:
                if self._depth[self._head[u]] < self._depth[self._head[v]]:
                    u, v = v, u
                u = self._parent[self._head[u]]

            return u if self._depth[u] < self._depth[v] else v

    def distance(self, u: int, v: int) -> int:
        """
        Find distance (number of edges) between u and v.
        """
        with self._lock:
            ancestor = self.lca(u, v)
            return (self._depth[u] - self._depth[ancestor] +
                   self._depth[v] - self._depth[ancestor])

    def kth_ancestor(self, u: int, k: int) -> int:
        """
        Find k-th ancestor of u.

        Returns -1 if no such ancestor exists.
        """
        with self._lock:
            while u != -1 and k > 0:
                head_u = self._head[u]

                # Distance to chain head
                dist_to_head = self._depth[u] - self._depth[head_u]

                if k <= dist_to_head:
                    # Answer is within current chain
                    target_depth = self._depth[u] - k
                    target_pos = self._position[u] - k
                    return self._pos_to_node[target_pos]

                # Jump to parent of chain head
                k -= dist_to_head + 1
                u = self._parent[head_u]

            return u

    def get_info(self) -> HLDInfo:
        """Get HLD information."""
        return HLDInfo(
            parent=self._parent,
            depth=self._depth,
            heavy=self._heavy,
            head=self._head,
            position=self._position,
            size=self._size
        )


# ============================================================================
# HLD WITH EDGE VALUES
# ============================================================================

class HLDEdge:
    """
    Heavy-Light Decomposition with edge values.

    "Ba'el decomposes edges too." — Ba'el
    """

    def __init__(
        self,
        n: int,
        edges: List[Tuple[int, int, int]],  # (u, v, weight)
        root: int = 0,
        combine: Callable[[int, int], int] = max,
        identity: int = 0
    ):
        """Initialize HLD with edge values."""
        self._n = n
        self._root = root
        self._combine = combine
        self._identity = identity
        self._lock = threading.RLock()

        # Build adjacency
        self._adj: List[List[Tuple[int, int]]] = [[] for _ in range(n)]
        for u, v, w in edges:
            self._adj[u].append((v, w))
            self._adj[v].append((u, w))

        # Store edge weights on lower endpoint
        self._edge_weight = [0] * n

        # Initialize HLD arrays
        self._parent = [-1] * n
        self._depth = [0] * n
        self._heavy = [-1] * n
        self._head = list(range(n))
        self._position = [0] * n
        self._size = [1] * n
        self._pos_to_node = [0] * n

        # Build HLD
        self._current_pos = 0
        self._dfs_size(root, -1, 0)
        self._dfs_hld(root, -1, root)

        # Build segment tree
        ordered_values = [self._edge_weight[self._pos_to_node[i]] for i in range(n)]
        self._segment_tree = SegmentTree(n, identity, combine)
        self._segment_tree.build(ordered_values)

    def _dfs_size(self, u: int, parent: int, weight: int):
        """First DFS: compute sizes and store edge weights."""
        self._parent[u] = parent
        self._edge_weight[u] = weight
        self._depth[u] = self._depth[parent] + 1 if parent >= 0 else 0

        max_child_size = 0

        for v, w in self._adj[u]:
            if v != parent:
                self._dfs_size(v, u, w)
                self._size[u] += self._size[v]

                if self._size[v] > max_child_size:
                    max_child_size = self._size[v]
                    self._heavy[u] = v

    def _dfs_hld(self, u: int, parent: int, head: int):
        """Second DFS: assign positions."""
        self._head[u] = head
        self._position[u] = self._current_pos
        self._pos_to_node[self._current_pos] = u
        self._current_pos += 1

        if self._heavy[u] != -1:
            self._dfs_hld(self._heavy[u], u, head)

        for v, w in self._adj[u]:
            if v != parent and v != self._heavy[u]:
                self._dfs_hld(v, u, v)

    def query_path(self, u: int, v: int) -> int:
        """
        Query on edges of path from u to v.
        """
        with self._lock:
            result = self._identity

            while self._head[u] != self._head[v]:
                if self._depth[self._head[u]] < self._depth[self._head[v]]:
                    u, v = v, u

                # Query segment (excluding chain head, as edge goes to parent)
                left = self._position[self._head[u]]
                right = self._position[u]
                result = self._combine(result, self._segment_tree.query(left, right))

                u = self._parent[self._head[u]]

            # Same chain - exclude LCA (edge is stored on lower node)
            if self._depth[u] > self._depth[v]:
                u, v = v, u

            if u != v:  # Don't include LCA's edge
                left = self._position[u] + 1
                right = self._position[v]
                if left <= right:
                    result = self._combine(result, self._segment_tree.query(left, right))

            return result

    def update_edge(self, u: int, v: int, weight: int):
        """
        Update edge weight.

        Edge is identified by its endpoints.
        """
        with self._lock:
            # Find which endpoint is the child
            if self._parent[u] == v:
                child = u
            elif self._parent[v] == u:
                child = v
            else:
                return  # Edge not found

            self._edge_weight[child] = weight
            self._segment_tree.update(self._position[child], weight)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_hld(
    n: int,
    edges: List[Tuple[int, int]],
    root: int = 0,
    values: Optional[List[int]] = None
) -> HeavyLightDecomposition:
    """Create HLD with node values."""
    return HeavyLightDecomposition(n, edges, root, values)


def create_hld_sum(
    n: int,
    edges: List[Tuple[int, int]],
    root: int = 0,
    values: Optional[List[int]] = None
) -> HeavyLightDecomposition:
    """Create HLD for path sums."""
    return HeavyLightDecomposition(
        n, edges, root, values,
        combine=lambda a, b: a + b,
        identity=0
    )


def create_hld_max(
    n: int,
    edges: List[Tuple[int, int]],
    root: int = 0,
    values: Optional[List[int]] = None
) -> HeavyLightDecomposition:
    """Create HLD for path maximum."""
    return HeavyLightDecomposition(
        n, edges, root, values,
        combine=max,
        identity=float('-inf')
    )


def create_hld_min(
    n: int,
    edges: List[Tuple[int, int]],
    root: int = 0,
    values: Optional[List[int]] = None
) -> HeavyLightDecomposition:
    """Create HLD for path minimum."""
    return HeavyLightDecomposition(
        n, edges, root, values,
        combine=min,
        identity=float('inf')
    )


def create_hld_edge(
    n: int,
    edges: List[Tuple[int, int, int]],
    root: int = 0
) -> HLDEdge:
    """Create HLD with edge values."""
    return HLDEdge(n, edges, root)


def path_sum(
    n: int,
    edges: List[Tuple[int, int]],
    values: List[int],
    u: int,
    v: int
) -> int:
    """Compute sum on path from u to v."""
    hld = create_hld_sum(n, edges, 0, values)
    return hld.query_path(u, v)


def lca(n: int, edges: List[Tuple[int, int]], u: int, v: int) -> int:
    """Find LCA of u and v."""
    hld = create_hld(n, edges)
    return hld.lca(u, v)
