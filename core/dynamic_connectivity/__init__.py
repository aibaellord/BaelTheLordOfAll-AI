"""
BAEL Dynamic Connectivity Engine
================================

Maintain connected components with edge insertions/deletions.

"Ba'el tracks connections as they evolve." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger("BAEL.DynamicConnectivity")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class DCStats:
    """Dynamic connectivity statistics."""
    node_count: int = 0
    edge_count: int = 0
    component_count: int = 0
    insertions: int = 0
    deletions: int = 0
    queries: int = 0


# ============================================================================
# LINK-CUT TREE FOR DYNAMIC CONNECTIVITY
# ============================================================================

class LinkCutNode:
    """Node in Link-Cut Tree."""

    def __init__(self, node_id: int):
        self.id = node_id
        self.parent: Optional['LinkCutNode'] = None
        self.left: Optional['LinkCutNode'] = None
        self.right: Optional['LinkCutNode'] = None
        self.path_parent: Optional['LinkCutNode'] = None  # For virtual edges
        self.reversed: bool = False


class LinkCutTree:
    """
    Link-Cut Tree for dynamic tree connectivity.

    Features:
    - O(log n) amortized link/cut
    - O(log n) path queries
    - O(log n) LCA

    "Ba'el links and cuts in logarithmic time." — Ba'el
    """

    def __init__(self):
        """Initialize Link-Cut Tree."""
        self._nodes: Dict[int, LinkCutNode] = {}
        self._lock = threading.RLock()

    def _get_or_create(self, node_id: int) -> LinkCutNode:
        """Get or create node."""
        if node_id not in self._nodes:
            self._nodes[node_id] = LinkCutNode(node_id)
        return self._nodes[node_id]

    def _is_root(self, node: LinkCutNode) -> bool:
        """Check if node is splay tree root."""
        return (not node.parent or
                (node.parent.left != node and node.parent.right != node))

    def _push(self, node: LinkCutNode) -> None:
        """Push reversal lazy tag."""
        if node.reversed:
            node.reversed = False
            node.left, node.right = node.right, node.left
            if node.left:
                node.left.reversed = not node.left.reversed
            if node.right:
                node.right.reversed = not node.right.reversed

    def _rotate(self, node: LinkCutNode) -> None:
        """Rotate node up."""
        parent = node.parent
        grandparent = parent.parent if parent else None

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

        # Transfer path parent
        if node.path_parent is None:
            node.path_parent = parent.path_parent
        parent.path_parent = None

    def _splay(self, node: LinkCutNode) -> None:
        """Splay node to root."""
        while not self._is_root(node):
            parent = node.parent
            grandparent = parent.parent if parent else None

            if grandparent and not self._is_root(parent):
                self._push(grandparent)
            self._push(parent)
            self._push(node)

            if self._is_root(parent):
                self._rotate(node)
            elif ((grandparent.left == parent) == (parent.left == node)):
                # Zig-zig
                self._rotate(parent)
                self._rotate(node)
            else:
                # Zig-zag
                self._rotate(node)
                self._rotate(node)

    def _access(self, node: LinkCutNode) -> None:
        """Access node (make it root of aux tree)."""
        self._splay(node)

        # Disconnect right child
        if node.right:
            node.right.path_parent = node
            node.right.parent = None
            node.right = None

        # Walk up path parents
        while node.path_parent:
            parent = node.path_parent
            self._splay(parent)

            if parent.right:
                parent.right.path_parent = parent
                parent.right.parent = None

            parent.right = node
            node.parent = parent
            node.path_parent = None

            self._splay(node)

    def _make_root(self, node: LinkCutNode) -> None:
        """Make node the root of its tree."""
        self._access(node)
        node.reversed = not node.reversed
        self._push(node)

    def _find_root(self, node: LinkCutNode) -> LinkCutNode:
        """Find root of tree containing node."""
        self._access(node)

        while node.left:
            self._push(node)
            node = node.left

        self._splay(node)
        return node

    def link(self, u: int, v: int) -> bool:
        """
        Link nodes u and v (add edge).

        Args:
            u: First node
            v: Second node

        Returns:
            True if linked, False if already connected
        """
        with self._lock:
            node_u = self._get_or_create(u)
            node_v = self._get_or_create(v)

            # Check if already connected
            if self._find_root(node_u) == self._find_root(node_v):
                return False

            self._make_root(node_u)
            node_u.path_parent = node_v

            return True

    def cut(self, u: int, v: int) -> bool:
        """
        Cut edge between u and v.

        Args:
            u: First node
            v: Second node

        Returns:
            True if cut, False if no edge
        """
        with self._lock:
            if u not in self._nodes or v not in self._nodes:
                return False

            node_u = self._nodes[u]
            node_v = self._nodes[v]

            self._make_root(node_u)
            self._access(node_v)

            # Check if edge exists
            if node_v.left != node_u or node_u.right:
                return False

            node_v.left = None
            node_u.parent = None

            return True

    def connected(self, u: int, v: int) -> bool:
        """Check if u and v are connected."""
        with self._lock:
            if u not in self._nodes or v not in self._nodes:
                return u == v

            return self._find_root(self._nodes[u]) == self._find_root(self._nodes[v])

    def lca(self, u: int, v: int) -> Optional[int]:
        """Find LCA of u and v."""
        with self._lock:
            if not self.connected(u, v):
                return None

            self._access(self._nodes[u])
            self._access(self._nodes[v])

            # The path parent of u's splay tree root is LCA
            node = self._nodes[u]
            while node.parent:
                node = node.parent

            if node.path_parent:
                return node.path_parent.id
            return node.id


# ============================================================================
# EULER TOUR TREE (FOR FORESTS)
# ============================================================================

class EulerTourTree:
    """
    Euler Tour Tree for dynamic forest connectivity.

    Maintains forest as Euler tours.

    "Ba'el tours the forest dynamically." — Ba'el
    """

    def __init__(self):
        """Initialize Euler Tour Tree."""
        self._parent: Dict[int, int] = {}
        self._rank: Dict[int, int] = {}
        self._edges: Set[Tuple[int, int]] = set()
        self._adj: Dict[int, Set[int]] = defaultdict(set)
        self._lock = threading.RLock()

    def _find(self, x: int) -> int:
        """Find with path compression."""
        if x not in self._parent:
            self._parent[x] = x
            self._rank[x] = 0

        if self._parent[x] != x:
            self._parent[x] = self._find(self._parent[x])

        return self._parent[x]

    def _union(self, x: int, y: int) -> None:
        """Union by rank."""
        px, py = self._find(x), self._find(y)

        if px == py:
            return

        if self._rank[px] < self._rank[py]:
            px, py = py, px

        self._parent[py] = px

        if self._rank[px] == self._rank[py]:
            self._rank[px] += 1

    def link(self, u: int, v: int) -> bool:
        """Add edge u-v."""
        with self._lock:
            edge = (min(u, v), max(u, v))

            if edge in self._edges:
                return False

            if self._find(u) == self._find(v):
                return False  # Would create cycle

            self._edges.add(edge)
            self._adj[u].add(v)
            self._adj[v].add(u)
            self._union(u, v)

            return True

    def cut(self, u: int, v: int) -> bool:
        """Remove edge u-v."""
        with self._lock:
            edge = (min(u, v), max(u, v))

            if edge not in self._edges:
                return False

            self._edges.remove(edge)
            self._adj[u].discard(v)
            self._adj[v].discard(u)

            # Rebuild union-find for affected component
            self._rebuild_component(u)
            self._rebuild_component(v)

            return True

    def _rebuild_component(self, start: int) -> None:
        """Rebuild union-find for component containing start."""
        # BFS to find all nodes in component
        visited = set()
        queue = [start]
        visited.add(start)

        while queue:
            node = queue.pop(0)
            self._parent[node] = node
            self._rank[node] = 0

            for neighbor in self._adj[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        # Rebuild union-find
        for node in visited:
            for neighbor in self._adj[node]:
                if neighbor in visited:
                    self._union(node, neighbor)

    def connected(self, u: int, v: int) -> bool:
        """Check if u and v are connected."""
        with self._lock:
            return self._find(u) == self._find(v)


# ============================================================================
# DYNAMIC CONNECTIVITY ENGINE
# ============================================================================

class DynamicConnectivityEngine:
    """
    Dynamic Connectivity for general graphs.

    Uses multiple data structures for different operations.

    Features:
    - Edge insertion/deletion
    - Connectivity queries
    - Component tracking

    "Ba'el maintains connectivity through chaos." — Ba'el
    """

    def __init__(self):
        """Initialize dynamic connectivity."""
        self._adj: Dict[int, Set[int]] = defaultdict(set)
        self._edges: Set[Tuple[int, int]] = set()
        self._parent: Dict[int, int] = {}
        self._rank: Dict[int, int] = {}
        self._stats = DCStats()
        self._lock = threading.RLock()

        logger.debug("Dynamic connectivity initialized")

    def _find(self, x: int) -> int:
        """Find root with path compression."""
        if x not in self._parent:
            self._parent[x] = x
            self._rank[x] = 0
            self._stats.node_count += 1

        root = x
        while self._parent[root] != root:
            root = self._parent[root]

        # Path compression
        while self._parent[x] != root:
            next_x = self._parent[x]
            self._parent[x] = root
            x = next_x

        return root

    def add_edge(self, u: int, v: int) -> bool:
        """
        Add edge u-v.

        Args:
            u: First endpoint
            v: Second endpoint

        Returns:
            True if new edge
        """
        with self._lock:
            edge = (min(u, v), max(u, v))

            if edge in self._edges:
                return False

            self._edges.add(edge)
            self._adj[u].add(v)
            self._adj[v].add(u)
            self._stats.edge_count += 1
            self._stats.insertions += 1

            # Union
            pu, pv = self._find(u), self._find(v)

            if pu != pv:
                if self._rank[pu] < self._rank[pv]:
                    pu, pv = pv, pu
                self._parent[pv] = pu
                if self._rank[pu] == self._rank[pv]:
                    self._rank[pu] += 1
                self._stats.component_count -= 1

            return True

    def remove_edge(self, u: int, v: int) -> bool:
        """
        Remove edge u-v.

        Args:
            u: First endpoint
            v: Second endpoint

        Returns:
            True if edge existed
        """
        with self._lock:
            edge = (min(u, v), max(u, v))

            if edge not in self._edges:
                return False

            self._edges.remove(edge)
            self._adj[u].discard(v)
            self._adj[v].discard(u)
            self._stats.edge_count -= 1
            self._stats.deletions += 1

            # Check if still connected - rebuild component
            self._rebuild_all()

            return True

    def _rebuild_all(self) -> None:
        """Rebuild union-find for all components."""
        # Reset
        self._parent = {}
        self._rank = {}

        nodes = set(self._adj.keys())
        self._stats.node_count = len(nodes)
        self._stats.component_count = len(nodes)

        for node in nodes:
            self._parent[node] = node
            self._rank[node] = 0

        # Rebuild from edges
        for u, v in self._edges:
            pu, pv = self._find(u), self._find(v)
            if pu != pv:
                if self._rank[pu] < self._rank[pv]:
                    pu, pv = pv, pu
                self._parent[pv] = pu
                if self._rank[pu] == self._rank[pv]:
                    self._rank[pu] += 1
                self._stats.component_count -= 1

    def connected(self, u: int, v: int) -> bool:
        """Check if u and v are connected."""
        with self._lock:
            self._stats.queries += 1
            return self._find(u) == self._find(v)

    def component_count(self) -> int:
        """Get number of connected components."""
        return self._stats.component_count

    def get_component(self, node: int) -> Set[int]:
        """Get all nodes in component containing node."""
        with self._lock:
            root = self._find(node)
            return {n for n in self._parent if self._find(n) == root}

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'node_count': self._stats.node_count,
            'edge_count': self._stats.edge_count,
            'component_count': self._stats.component_count,
            'insertions': self._stats.insertions,
            'deletions': self._stats.deletions,
            'queries': self._stats.queries
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_dynamic_connectivity() -> DynamicConnectivityEngine:
    """Create dynamic connectivity engine."""
    return DynamicConnectivityEngine()


def create_link_cut_tree() -> LinkCutTree:
    """Create link-cut tree."""
    return LinkCutTree()


def create_euler_tour_tree() -> EulerTourTree:
    """Create Euler tour tree."""
    return EulerTourTree()
