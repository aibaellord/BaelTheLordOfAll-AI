"""
BAEL Tree Properties Engine
===========================

Tree diameter, center, radius, and other properties.

"Ba'el measures the reach of trees." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque

logger = logging.getLogger("BAEL.TreeProperties")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class TreeProperties:
    """Tree property results."""
    diameter: int = 0
    radius: int = 0
    center: List[int] = field(default_factory=list)
    diameter_path: List[int] = field(default_factory=list)
    eccentricity: Dict[int, int] = field(default_factory=dict)


@dataclass
class TreeStats:
    """Tree statistics."""
    node_count: int = 0
    edge_count: int = 0
    height: int = 0
    is_tree: bool = True


# ============================================================================
# TREE DIAMETER ENGINE
# ============================================================================

class TreeDiameter:
    """
    Tree diameter computation.

    Features:
    - O(n) two-BFS approach
    - Path reconstruction
    - Works for weighted trees

    "Ba'el finds the longest path." — Ba'el
    """

    def __init__(self):
        """Initialize tree diameter."""
        self._adj: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
        self._nodes: Set[int] = set()
        self._lock = threading.RLock()

        logger.debug("Tree diameter initialized")

    def add_edge(self, u: int, v: int, weight: int = 1) -> None:
        """Add undirected edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].append((v, weight))
            self._adj[v].append((u, weight))

    def _bfs_farthest(self, start: int) -> Tuple[int, int, Dict[int, int]]:
        """
        BFS to find farthest node.

        Returns:
            (farthest_node, distance, dist_map)
        """
        dist = {node: -1 for node in self._nodes}
        dist[start] = 0

        queue = deque([start])
        farthest = start
        max_dist = 0

        while queue:
            node = queue.popleft()

            for neighbor, weight in self._adj[node]:
                if dist[neighbor] == -1:
                    dist[neighbor] = dist[node] + weight
                    queue.append(neighbor)

                    if dist[neighbor] > max_dist:
                        max_dist = dist[neighbor]
                        farthest = neighbor

        return farthest, max_dist, dist

    def find_diameter(self) -> int:
        """
        Find tree diameter.

        Returns:
            Diameter length
        """
        with self._lock:
            if not self._nodes:
                return 0

            start = next(iter(self._nodes))

            # First BFS from arbitrary node
            u, _, _ = self._bfs_farthest(start)

            # Second BFS from farthest node
            _, diameter, _ = self._bfs_farthest(u)

            return diameter

    def find_diameter_path(self) -> List[int]:
        """
        Find the diameter path.

        Returns:
            List of nodes in diameter path
        """
        with self._lock:
            if not self._nodes:
                return []

            start = next(iter(self._nodes))

            # First BFS
            u, _, _ = self._bfs_farthest(start)

            # Second BFS with parent tracking
            parent = {u: None}
            dist = {node: -1 for node in self._nodes}
            dist[u] = 0

            queue = deque([u])
            farthest = u
            max_dist = 0

            while queue:
                node = queue.popleft()

                for neighbor, weight in self._adj[node]:
                    if dist[neighbor] == -1:
                        dist[neighbor] = dist[node] + weight
                        parent[neighbor] = node
                        queue.append(neighbor)

                        if dist[neighbor] > max_dist:
                            max_dist = dist[neighbor]
                            farthest = neighbor

            # Reconstruct path
            path = []
            current = farthest
            while current is not None:
                path.append(current)
                current = parent.get(current)

            path.reverse()
            return path


# ============================================================================
# TREE CENTER ENGINE
# ============================================================================

class TreeCenter:
    """
    Tree center and eccentricity computation.

    Features:
    - O(n) leaf stripping approach
    - Finds 1 or 2 center nodes
    - Computes all eccentricities

    "Ba'el finds the heart of the tree." — Ba'el
    """

    def __init__(self):
        """Initialize tree center."""
        self._adj: Dict[int, Set[int]] = defaultdict(set)
        self._nodes: Set[int] = set()
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int) -> None:
        """Add undirected edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].add(v)
            self._adj[v].add(u)

    def find_center(self) -> List[int]:
        """
        Find tree center(s) using leaf stripping.

        Returns:
            List of 1 or 2 center nodes
        """
        with self._lock:
            if not self._nodes:
                return []

            if len(self._nodes) == 1:
                return list(self._nodes)

            # Copy adjacency
            adj = {node: set(neighbors) for node, neighbors in self._adj.items()}
            remaining = set(self._nodes)

            while len(remaining) > 2:
                # Find leaves (degree 1)
                leaves = [n for n in remaining if len(adj[n]) == 1]

                # Remove leaves
                for leaf in leaves:
                    remaining.remove(leaf)

                    for neighbor in adj[leaf]:
                        adj[neighbor].discard(leaf)

            return list(remaining)

    def compute_eccentricity(self) -> Dict[int, int]:
        """
        Compute eccentricity for all nodes.

        Eccentricity = max distance to any other node
        """
        with self._lock:
            eccentricity = {}

            for node in self._nodes:
                # BFS from this node
                dist = {node: 0}
                queue = deque([node])
                max_dist = 0

                while queue:
                    current = queue.popleft()

                    for neighbor in self._adj[current]:
                        if neighbor not in dist:
                            dist[neighbor] = dist[current] + 1
                            max_dist = max(max_dist, dist[neighbor])
                            queue.append(neighbor)

                eccentricity[node] = max_dist

            return eccentricity

    def find_radius(self) -> int:
        """Find tree radius (minimum eccentricity)."""
        eccentricity = self.compute_eccentricity()
        return min(eccentricity.values()) if eccentricity else 0

    def get_all_properties(self) -> TreeProperties:
        """Get all tree properties."""
        with self._lock:
            eccentricity = self.compute_eccentricity()

            if not eccentricity:
                return TreeProperties()

            diameter = max(eccentricity.values())
            radius = min(eccentricity.values())
            center = [n for n, e in eccentricity.items() if e == radius]

            # Get diameter path using TreeDiameter
            td = TreeDiameter()
            for u in self._adj:
                for v in self._adj[u]:
                    if u < v:
                        td.add_edge(u, v)

            diameter_path = td.find_diameter_path()

            return TreeProperties(
                diameter=diameter,
                radius=radius,
                center=center,
                diameter_path=diameter_path,
                eccentricity=eccentricity
            )


# ============================================================================
# TREE ISOMORPHISM
# ============================================================================

class TreeIsomorphism:
    """
    Tree isomorphism testing.

    Features:
    - O(n log n) canonical hash
    - Center-based rooting
    - AHU algorithm inspired

    "Ba'el recognizes structural equivalence." — Ba'el
    """

    def __init__(self):
        """Initialize tree isomorphism."""
        self._adj: Dict[int, Set[int]] = defaultdict(set)
        self._nodes: Set[int] = set()
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int) -> None:
        """Add undirected edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].add(v)
            self._adj[v].add(u)

    def _compute_hash(self, root: int) -> str:
        """Compute canonical hash rooted at given node."""
        def dfs(node: int, parent: Optional[int]) -> str:
            child_hashes = []

            for child in self._adj[node]:
                if child != parent:
                    child_hashes.append(dfs(child, node))

            child_hashes.sort()
            return "(" + "".join(child_hashes) + ")"

        return dfs(root, None)

    def canonical_hash(self) -> str:
        """
        Compute canonical hash for the tree.

        Returns:
            Canonical string hash
        """
        with self._lock:
            if not self._nodes:
                return "()"

            # Find center(s)
            center = TreeCenter()
            for u in self._adj:
                for v in self._adj[u]:
                    if u < v:
                        center.add_edge(u, v)

            centers = center.find_center()

            if len(centers) == 1:
                return self._compute_hash(centers[0])
            else:
                # Two centers - use edge between them
                h1 = self._compute_hash(centers[0])
                h2 = self._compute_hash(centers[1])

                if h1 < h2:
                    return f"[{h1},{h2}]"
                else:
                    return f"[{h2},{h1}]"

    @staticmethod
    def are_isomorphic(tree1: 'TreeIsomorphism', tree2: 'TreeIsomorphism') -> bool:
        """Check if two trees are isomorphic."""
        return tree1.canonical_hash() == tree2.canonical_hash()


# ============================================================================
# LOWEST COMMON ANCESTOR (ONLINE)
# ============================================================================

class OnlineLCA:
    """
    Online LCA with O(n log n) preprocessing.

    Features:
    - Binary lifting approach
    - O(log n) per query
    - Also computes depth, distance

    "Ba'el finds the common ancestor instantly." — Ba'el
    """

    def __init__(self):
        """Initialize online LCA."""
        self._adj: Dict[int, List[int]] = defaultdict(list)
        self._nodes: Set[int] = set()
        self._root: Optional[int] = None

        self._depth: Dict[int, int] = {}
        self._parent: Dict[int, List[Optional[int]]] = {}
        self._log_n = 0
        self._built = False
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int) -> None:
        """Add undirected edge."""
        with self._lock:
            self._built = False
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].append(v)
            self._adj[v].append(u)

    def build(self, root: Optional[int] = None) -> None:
        """Build LCA structure rooted at given node."""
        with self._lock:
            if self._built:
                return

            if not self._nodes:
                return

            self._root = root if root is not None else next(iter(self._nodes))

            n = len(self._nodes)
            self._log_n = max(1, (n - 1).bit_length())

            self._depth = {}
            self._parent = {node: [None] * self._log_n for node in self._nodes}

            # BFS to set depths and immediate parents
            queue = deque([self._root])
            self._depth[self._root] = 0

            while queue:
                node = queue.popleft()

                for child in self._adj[node]:
                    if child not in self._depth:
                        self._depth[child] = self._depth[node] + 1
                        self._parent[child][0] = node
                        queue.append(child)

            # Build binary lifting table
            for j in range(1, self._log_n):
                for node in self._nodes:
                    p = self._parent[node][j - 1]
                    if p is not None:
                        self._parent[node][j] = self._parent[p][j - 1]

            self._built = True

    def lca(self, u: int, v: int) -> int:
        """
        Find lowest common ancestor of u and v.

        Returns:
            LCA node
        """
        self.build()

        with self._lock:
            if self._depth[u] < self._depth[v]:
                u, v = v, u

            # Bring to same depth
            diff = self._depth[u] - self._depth[v]
            for j in range(self._log_n):
                if diff & (1 << j):
                    u = self._parent[u][j]

            if u == v:
                return u

            # Binary search for LCA
            for j in range(self._log_n - 1, -1, -1):
                if self._parent[u][j] != self._parent[v][j]:
                    u = self._parent[u][j]
                    v = self._parent[v][j]

            return self._parent[u][0]

    def distance(self, u: int, v: int) -> int:
        """Get distance between two nodes."""
        self.build()

        with self._lock:
            ancestor = self.lca(u, v)
            return self._depth[u] + self._depth[v] - 2 * self._depth[ancestor]

    def kth_ancestor(self, node: int, k: int) -> Optional[int]:
        """Get k-th ancestor of node."""
        self.build()

        with self._lock:
            for j in range(self._log_n):
                if k & (1 << j):
                    node = self._parent[node][j]
                    if node is None:
                        return None
            return node

    def get_depth(self, node: int) -> int:
        """Get depth of node."""
        self.build()
        return self._depth.get(node, -1)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_tree_diameter() -> TreeDiameter:
    """Create tree diameter engine."""
    return TreeDiameter()


def create_tree_center() -> TreeCenter:
    """Create tree center engine."""
    return TreeCenter()


def create_tree_isomorphism() -> TreeIsomorphism:
    """Create tree isomorphism engine."""
    return TreeIsomorphism()


def create_online_lca() -> OnlineLCA:
    """Create online LCA engine."""
    return OnlineLCA()


def tree_diameter(edges: List[Tuple[int, int]]) -> int:
    """Get diameter of unweighted tree."""
    engine = TreeDiameter()
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.find_diameter()


def tree_center(edges: List[Tuple[int, int]]) -> List[int]:
    """Get center node(s) of tree."""
    engine = TreeCenter()
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.find_center()


def tree_radius(edges: List[Tuple[int, int]]) -> int:
    """Get radius of tree."""
    engine = TreeCenter()
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.find_radius()


def trees_isomorphic(
    tree1_edges: List[Tuple[int, int]],
    tree2_edges: List[Tuple[int, int]]
) -> bool:
    """Check if two trees are isomorphic."""
    t1 = TreeIsomorphism()
    for u, v in tree1_edges:
        t1.add_edge(u, v)

    t2 = TreeIsomorphism()
    for u, v in tree2_edges:
        t2.add_edge(u, v)

    return TreeIsomorphism.are_isomorphic(t1, t2)
