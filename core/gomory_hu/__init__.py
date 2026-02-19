"""
BAEL Gomory-Hu Tree Engine
==========================

All-pairs minimum cut in undirected graphs.

"Ba'el finds the weakest links between all pairs." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque

logger = logging.getLogger("BAEL.GomoryHu")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class GomoryHuStats:
    """Gomory-Hu tree statistics."""
    node_count: int = 0
    edge_count: int = 0
    min_cut_calls: int = 0
    tree_edges: int = 0


@dataclass
class MinCutResult:
    """Result of min-cut computation."""
    value: int
    source_side: Set[int]
    sink_side: Set[int]


# ============================================================================
# MAX FLOW FOR MIN-CUT (EDMONDS-KARP)
# ============================================================================

class MaxFlow:
    """Max flow using Edmonds-Karp (BFS-based Ford-Fulkerson)."""

    def __init__(self, nodes: Set[int]):
        """Initialize max flow."""
        self._nodes = nodes
        self._capacity: Dict[Tuple[int, int], int] = defaultdict(int)
        self._adj: Dict[int, Set[int]] = defaultdict(set)

    def add_edge(self, u: int, v: int, capacity: int) -> None:
        """Add undirected edge with capacity."""
        self._capacity[(u, v)] += capacity
        self._capacity[(v, u)] += capacity
        self._adj[u].add(v)
        self._adj[v].add(u)

    def min_cut(self, source: int, sink: int) -> MinCutResult:
        """
        Find min s-t cut.

        Returns:
            MinCutResult with cut value and partition
        """
        # Create residual graph
        residual: Dict[Tuple[int, int], int] = dict(self._capacity)

        def bfs_path() -> Optional[List[int]]:
            """BFS for augmenting path."""
            parent = {source: None}
            queue = deque([source])

            while queue:
                u = queue.popleft()

                for v in self._adj[u]:
                    if v not in parent and residual.get((u, v), 0) > 0:
                        parent[v] = u

                        if v == sink:
                            # Reconstruct path
                            path = []
                            current = v
                            while current is not None:
                                path.append(current)
                                current = parent[current]
                            return path[::-1]

                        queue.append(v)

            return None

        # Find max flow
        total_flow = 0

        while True:
            path = bfs_path()
            if path is None:
                break

            # Find bottleneck
            flow = float('inf')
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                flow = min(flow, residual.get((u, v), 0))

            # Update residual
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                residual[(u, v)] = residual.get((u, v), 0) - flow
                residual[(v, u)] = residual.get((v, u), 0) + flow

            total_flow += flow

        # Find source side (reachable from source in residual)
        source_side = set()
        queue = deque([source])
        source_side.add(source)

        while queue:
            u = queue.popleft()
            for v in self._adj[u]:
                if v not in source_side and residual.get((u, v), 0) > 0:
                    source_side.add(v)
                    queue.append(v)

        sink_side = self._nodes - source_side

        return MinCutResult(
            value=total_flow,
            source_side=source_side,
            sink_side=sink_side
        )


# ============================================================================
# GOMORY-HU TREE ENGINE
# ============================================================================

class GomoryHuTreeEngine:
    """
    Gomory-Hu Tree construction.

    Features:
    - O((V-1) * MaxFlow) construction
    - O(V) min-cut query for any pair
    - Compact representation of all cuts

    "Ba'el encodes all cuts in a single tree." — Ba'el
    """

    def __init__(self):
        """Initialize Gomory-Hu tree engine."""
        self._nodes: Set[int] = set()
        self._edges: Dict[Tuple[int, int], int] = {}
        self._adj: Dict[int, Set[int]] = defaultdict(set)

        # Gomory-Hu tree
        self._tree_parent: Dict[int, int] = {}
        self._tree_weight: Dict[int, int] = {}
        self._tree_adj: Dict[int, List[Tuple[int, int]]] = defaultdict(list)

        self._stats = GomoryHuStats()
        self._built = False
        self._lock = threading.RLock()

        logger.debug("Gomory-Hu tree engine initialized")

    def add_edge(self, u: int, v: int, capacity: int) -> None:
        """Add undirected edge with capacity."""
        with self._lock:
            self._built = False
            self._nodes.add(u)
            self._nodes.add(v)

            edge = (min(u, v), max(u, v))
            self._edges[edge] = self._edges.get(edge, 0) + capacity
            self._adj[u].add(v)
            self._adj[v].add(u)

    def build(self) -> None:
        """Build Gomory-Hu tree."""
        with self._lock:
            if self._built:
                return

            if len(self._nodes) < 2:
                self._built = True
                return

            self._stats.node_count = len(self._nodes)
            self._stats.edge_count = len(self._edges)

            nodes = list(self._nodes)
            n = len(nodes)

            # Initialize: all nodes in same group, parent is first node
            group = {node: nodes[0] for node in nodes}

            self._tree_parent = {}
            self._tree_weight = {}

            for i in range(1, n):
                s = nodes[i]
                t = group[s]

                # Compute min s-t cut
                flow_graph = MaxFlow(self._nodes)
                for (u, v), cap in self._edges.items():
                    flow_graph.add_edge(u, v, cap)

                cut = flow_graph.min_cut(s, t)
                self._stats.min_cut_calls += 1

                # Update tree
                self._tree_parent[s] = t
                self._tree_weight[s] = cut.value

                # Update groups
                for node in cut.source_side:
                    if node != s and group[node] == t:
                        group[node] = s

                # Check if t's parent is on s's side
                if t in self._tree_parent:
                    t_parent = self._tree_parent[t]
                    if t_parent in cut.source_side:
                        # Reparent s to t's parent
                        self._tree_parent[s] = t_parent
                        self._tree_weight[s] = self._tree_weight[t]

                        # Update t's parent and weight
                        self._tree_parent[t] = s
                        self._tree_weight[t] = cut.value

            # Build adjacency list for tree
            self._tree_adj.clear()
            for node, parent in self._tree_parent.items():
                weight = self._tree_weight[node]
                self._tree_adj[node].append((parent, weight))
                self._tree_adj[parent].append((node, weight))

            self._stats.tree_edges = len(self._tree_parent)
            self._built = True

            logger.info(f"Gomory-Hu tree built: {n} nodes, "
                       f"{self._stats.min_cut_calls} min-cut calls")

    def min_cut(self, s: int, t: int) -> int:
        """
        Get minimum cut value between s and t.

        Args:
            s: Source node
            t: Sink node

        Returns:
            Minimum cut value
        """
        self.build()

        if s == t:
            return float('inf')

        if s not in self._nodes or t not in self._nodes:
            return 0

        # Find min edge on path from s to t in tree
        min_weight = float('inf')

        # BFS in tree
        visited = {s}
        queue = deque([(s, float('inf'))])

        while queue:
            node, path_min = queue.popleft()

            if node == t:
                return path_min

            for neighbor, weight in self._tree_adj[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, min(path_min, weight)))

        return 0  # Not connected

    def get_all_min_cuts(self) -> Dict[Tuple[int, int], int]:
        """
        Get all pairwise minimum cuts.

        Returns:
            Dict mapping (u, v) → min cut value
        """
        self.build()

        result = {}
        nodes = list(self._nodes)

        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                u, v = nodes[i], nodes[j]
                result[(u, v)] = self.min_cut(u, v)

        return result

    def get_tree_edges(self) -> List[Tuple[int, int, int]]:
        """Get Gomory-Hu tree edges as (u, v, weight)."""
        self.build()
        return [(node, parent, self._tree_weight[node])
                for node, parent in self._tree_parent.items()]

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        self.build()
        return {
            'node_count': self._stats.node_count,
            'edge_count': self._stats.edge_count,
            'min_cut_calls': self._stats.min_cut_calls,
            'tree_edges': self._stats.tree_edges
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_gomory_hu_tree() -> GomoryHuTreeEngine:
    """Create Gomory-Hu tree engine."""
    return GomoryHuTreeEngine()


def build_gomory_hu_tree(
    edges: List[Tuple[int, int, int]]
) -> GomoryHuTreeEngine:
    """
    Build Gomory-Hu tree from edges.

    Args:
        edges: List of (u, v, capacity) edges

    Returns:
        Built Gomory-Hu tree
    """
    engine = GomoryHuTreeEngine()
    for u, v, cap in edges:
        engine.add_edge(u, v, cap)
    engine.build()
    return engine


def all_pairs_min_cut(
    edges: List[Tuple[int, int, int]]
) -> Dict[Tuple[int, int], int]:
    """
    Compute all pairs minimum cuts.

    Args:
        edges: List of (u, v, capacity) edges

    Returns:
        Dict mapping (u, v) → min cut value
    """
    engine = build_gomory_hu_tree(edges)
    return engine.get_all_min_cuts()


def min_cut_between(
    edges: List[Tuple[int, int, int]],
    s: int,
    t: int
) -> int:
    """
    Get minimum cut between s and t.

    Args:
        edges: List of (u, v, capacity) edges
        s: Source
        t: Sink

    Returns:
        Minimum cut value
    """
    engine = build_gomory_hu_tree(edges)
    return engine.min_cut(s, t)
