"""
BAEL Tarjan's Offline LCA Engine
================================

Batch LCA queries using disjoint set union.

"Ba'el answers ancestors in bulk." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger("BAEL.OfflineLCA")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class LCAQuery:
    """LCA query."""
    id: int
    u: int
    v: int
    result: Optional[int] = None


@dataclass
class OfflineLCAStats:
    """Offline LCA statistics."""
    node_count: int = 0
    query_count: int = 0
    queries_answered: int = 0


# ============================================================================
# TARJAN'S OFFLINE LCA ENGINE
# ============================================================================

class OfflineLCAEngine:
    """
    Tarjan's Offline LCA algorithm.

    Features:
    - O(n + q * α(n)) for all queries
    - Union-Find with path compression
    - Batch query processing

    "Ba'el computes ancestry with set fusion." — Ba'el
    """

    def __init__(self, root: int):
        """
        Initialize offline LCA engine.

        Args:
            root: Root node of tree
        """
        self._root = root
        self._adj: Dict[int, List[int]] = defaultdict(list)
        self._nodes: Set[int] = {root}
        self._queries: List[LCAQuery] = []
        self._query_map: Dict[int, List[LCAQuery]] = defaultdict(list)

        # Union-Find
        self._parent: Dict[int, int] = {}
        self._rank: Dict[int, int] = {}
        self._ancestor: Dict[int, int] = {}
        self._visited: Set[int] = set()

        self._stats = OfflineLCAStats()
        self._lock = threading.RLock()

        logger.debug(f"Offline LCA engine initialized with root {root}")

    def add_edge(self, parent: int, child: int) -> None:
        """Add tree edge (parent → child)."""
        with self._lock:
            self._nodes.add(parent)
            self._nodes.add(child)
            self._adj[parent].append(child)

    def add_query(self, u: int, v: int) -> int:
        """
        Add LCA query for (u, v).

        Args:
            u: First node
            v: Second node

        Returns:
            Query ID
        """
        with self._lock:
            query_id = len(self._queries)
            query = LCAQuery(id=query_id, u=u, v=v)

            self._queries.append(query)
            self._query_map[u].append(query)
            self._query_map[v].append(query)

            return query_id

    def _find(self, x: int) -> int:
        """Find with path compression."""
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

    def _tarjan_lca(self, u: int) -> None:
        """Tarjan's LCA DFS."""
        # Make set for u
        self._parent[u] = u
        self._rank[u] = 0
        self._ancestor[u] = u

        # Process children
        for v in self._adj[u]:
            self._tarjan_lca(v)
            self._union(u, v)
            self._ancestor[self._find(u)] = u

        self._visited.add(u)

        # Answer queries
        for query in self._query_map[u]:
            other = query.v if query.u == u else query.u

            if other in self._visited and query.result is None:
                query.result = self._ancestor[self._find(other)]
                self._stats.queries_answered += 1

    def solve(self) -> Dict[int, int]:
        """
        Solve all LCA queries.

        Returns:
            Dict mapping query_id → LCA result
        """
        with self._lock:
            self._parent.clear()
            self._rank.clear()
            self._ancestor.clear()
            self._visited.clear()
            self._stats.queries_answered = 0

            self._stats.node_count = len(self._nodes)
            self._stats.query_count = len(self._queries)

            # Run Tarjan's algorithm
            self._tarjan_lca(self._root)

            # Collect results
            results = {q.id: q.result for q in self._queries}

            logger.info(f"Offline LCA: {self._stats.queries_answered}/{len(self._queries)} queries answered")

            return results

    def get_lca(self, query_id: int) -> Optional[int]:
        """Get result of specific query."""
        if query_id < len(self._queries):
            return self._queries[query_id].result
        return None

    def get_all_results(self) -> List[Tuple[int, int, int]]:
        """Get all query results as (u, v, lca) tuples."""
        return [(q.u, q.v, q.result) for q in self._queries]

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'node_count': self._stats.node_count,
            'query_count': self._stats.query_count,
            'queries_answered': self._stats.queries_answered
        }


# ============================================================================
# BATCH LCA WITH BINARY LIFTING (ONLINE PREPROCESSING)
# ============================================================================

class BinaryLiftingLCA:
    """
    Binary Lifting LCA for online queries after preprocessing.

    Features:
    - O(n log n) preprocessing
    - O(log n) per query
    - Works for any tree

    "Ba'el lifts through the ancestors." — Ba'el
    """

    def __init__(self, root: int):
        """Initialize binary lifting LCA."""
        self._root = root
        self._adj: Dict[int, List[int]] = defaultdict(list)
        self._nodes: Set[int] = {root}

        # Binary lifting tables
        self._depth: Dict[int, int] = {}
        self._up: Dict[int, List[int]] = {}
        self._log = 0

        self._built = False
        self._lock = threading.RLock()

    def add_edge(self, parent: int, child: int) -> None:
        """Add tree edge."""
        with self._lock:
            self._built = False
            self._nodes.add(parent)
            self._nodes.add(child)
            self._adj[parent].append(child)

    def build(self) -> None:
        """Build binary lifting table."""
        with self._lock:
            if self._built:
                return

            n = len(self._nodes)
            self._log = max(1, n.bit_length())

            # BFS to compute depths and initial parents
            self._depth = {self._root: 0}
            self._up = {node: [self._root] * self._log for node in self._nodes}

            queue = [self._root]
            self._up[self._root] = [self._root] * self._log

            while queue:
                u = queue.pop(0)
                for v in self._adj[u]:
                    self._depth[v] = self._depth[u] + 1
                    self._up[v][0] = u

                    # Build sparse table
                    for k in range(1, self._log):
                        self._up[v][k] = self._up[self._up[v][k - 1]][k - 1]

                    queue.append(v)

            self._built = True

    def lca(self, u: int, v: int) -> int:
        """
        Find LCA of u and v.

        Args:
            u: First node
            v: Second node

        Returns:
            LCA node
        """
        self.build()

        # Ensure u is deeper
        if self._depth[u] < self._depth[v]:
            u, v = v, u

        diff = self._depth[u] - self._depth[v]

        # Lift u to same depth as v
        for k in range(self._log):
            if (diff >> k) & 1:
                u = self._up[u][k]

        if u == v:
            return u

        # Binary search for LCA
        for k in range(self._log - 1, -1, -1):
            if self._up[u][k] != self._up[v][k]:
                u = self._up[u][k]
                v = self._up[v][k]

        return self._up[u][0]

    def distance(self, u: int, v: int) -> int:
        """Find distance between u and v."""
        self.build()
        ancestor = self.lca(u, v)
        return self._depth[u] + self._depth[v] - 2 * self._depth[ancestor]

    def kth_ancestor(self, u: int, k: int) -> Optional[int]:
        """Find k-th ancestor of u."""
        self.build()

        if k > self._depth[u]:
            return None

        for i in range(self._log):
            if (k >> i) & 1:
                u = self._up[u][i]

        return u


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_offline_lca(root: int) -> OfflineLCAEngine:
    """Create offline LCA engine."""
    return OfflineLCAEngine(root)


def create_binary_lifting_lca(root: int) -> BinaryLiftingLCA:
    """Create binary lifting LCA."""
    return BinaryLiftingLCA(root)


def batch_lca(
    root: int,
    edges: List[Tuple[int, int]],
    queries: List[Tuple[int, int]]
) -> List[int]:
    """
    Batch LCA queries.

    Args:
        root: Tree root
        edges: List of (parent, child) edges
        queries: List of (u, v) queries

    Returns:
        List of LCA results
    """
    engine = OfflineLCAEngine(root)

    for parent, child in edges:
        engine.add_edge(parent, child)

    for u, v in queries:
        engine.add_query(u, v)

    engine.solve()

    return [engine.get_lca(i) for i in range(len(queries))]


def online_lca_setup(
    root: int,
    edges: List[Tuple[int, int]]
) -> BinaryLiftingLCA:
    """
    Set up online LCA structure.

    Args:
        root: Tree root
        edges: List of (parent, child) edges

    Returns:
        BinaryLiftingLCA ready for queries
    """
    lca = BinaryLiftingLCA(root)

    for parent, child in edges:
        lca.add_edge(parent, child)

    lca.build()
    return lca
