"""
BAEL Steiner Tree Engine
========================

Steiner tree algorithms for connecting terminal sets.

"Ba'el connects the chosen ones optimally." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import heapq

logger = logging.getLogger("BAEL.SteinerTree")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SteinerResult:
    """Steiner tree result."""
    edges: List[Tuple[int, int, float]] = field(default_factory=list)
    steiner_vertices: Set[int] = field(default_factory=set)
    total_weight: float = 0.0
    is_optimal: bool = False


@dataclass
class SteinerStats:
    """Steiner tree statistics."""
    terminal_count: int = 0
    steiner_count: int = 0
    total_nodes: int = 0
    total_weight: float = 0.0


# ============================================================================
# STEINER TREE - SHORTEST PATH HEURISTIC
# ============================================================================

class ShortestPathSteiner:
    """
    Steiner tree using shortest path heuristic.

    Features:
    - O(k * V² log V) for k terminals
    - 2(1 - 1/l)-approximation
    - Simple and practical

    "Ba'el connects via shortest routes." — Ba'el
    """

    def __init__(self):
        """Initialize shortest path Steiner."""
        self._adj: Dict[int, List[Tuple[int, float]]] = defaultdict(list)
        self._nodes: Set[int] = set()
        self._stats = SteinerStats()
        self._lock = threading.RLock()

        logger.debug("Shortest path Steiner initialized")

    def add_edge(self, u: int, v: int, weight: float) -> None:
        """Add undirected weighted edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].append((v, weight))
            self._adj[v].append((u, weight))

    def _dijkstra(self, source: int) -> Tuple[Dict[int, float], Dict[int, Optional[int]]]:
        """Dijkstra from source."""
        dist = {node: float('inf') for node in self._nodes}
        parent = {node: None for node in self._nodes}
        dist[source] = 0.0

        heap = [(0.0, source)]

        while heap:
            d, u = heapq.heappop(heap)

            if d > dist[u]:
                continue

            for v, w in self._adj[u]:
                if dist[u] + w < dist[v]:
                    dist[v] = dist[u] + w
                    parent[v] = u
                    heapq.heappush(heap, (dist[v], v))

        return dist, parent

    def find_steiner_tree(self, terminals: Set[int]) -> SteinerResult:
        """
        Find Steiner tree connecting terminals.

        Uses shortest path heuristic (iterative).

        Args:
            terminals: Set of terminal vertices to connect

        Returns:
            SteinerResult with Steiner tree
        """
        with self._lock:
            if len(terminals) <= 1:
                return SteinerResult(is_optimal=True)

            terminals = set(terminals)
            tree_nodes = set()
            tree_edges = []
            total_weight = 0.0

            # Start with first terminal
            start = next(iter(terminals))
            tree_nodes.add(start)
            remaining = terminals - {start}

            while remaining:
                # Find shortest path from tree to any remaining terminal
                best_path = None
                best_dist = float('inf')
                best_terminal = None

                for t in remaining:
                    dist, parent = self._dijkstra(t)

                    # Find closest tree node
                    for tree_node in tree_nodes:
                        if dist[tree_node] < best_dist:
                            best_dist = dist[tree_node]
                            best_terminal = t

                            # Reconstruct path
                            path = []
                            current = tree_node
                            while current is not None and current != t:
                                next_node = parent[current]
                                if next_node is not None:
                                    path.append((current, next_node))
                                current = next_node

                            best_path = path

                if best_path is None:
                    break

                # Add path to tree
                remaining.remove(best_terminal)

                for u, v in best_path:
                    if u not in tree_nodes or v not in tree_nodes:
                        # Find edge weight
                        weight = 0.0
                        for neighbor, w in self._adj[u]:
                            if neighbor == v:
                                weight = w
                                break

                        tree_edges.append((u, v, weight))
                        total_weight += weight

                    tree_nodes.add(u)
                    tree_nodes.add(v)

            steiner_vertices = tree_nodes - terminals

            self._stats.terminal_count = len(terminals)
            self._stats.steiner_count = len(steiner_vertices)
            self._stats.total_nodes = len(tree_nodes)
            self._stats.total_weight = total_weight

            return SteinerResult(
                edges=tree_edges,
                steiner_vertices=steiner_vertices,
                total_weight=total_weight,
                is_optimal=False
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'terminal_count': self._stats.terminal_count,
            'steiner_count': self._stats.steiner_count,
            'total_nodes': self._stats.total_nodes,
            'total_weight': self._stats.total_weight
        }


# ============================================================================
# STEINER TREE - MST HEURISTIC
# ============================================================================

class MSTSteiner:
    """
    Steiner tree using MST of terminal metric closure.

    Features:
    - Build complete graph on terminals with shortest path distances
    - Find MST of this graph
    - Map back to original edges
    - 2-approximation

    "Ba'el spans the terminal graph." — Ba'el
    """

    def __init__(self):
        """Initialize MST Steiner."""
        self._adj: Dict[int, List[Tuple[int, float]]] = defaultdict(list)
        self._nodes: Set[int] = set()
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int, weight: float) -> None:
        """Add undirected weighted edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].append((v, weight))
            self._adj[v].append((u, weight))

    def _dijkstra_full(self, source: int) -> Tuple[Dict[int, float], Dict[int, List[int]]]:
        """Dijkstra with path reconstruction."""
        dist = {node: float('inf') for node in self._nodes}
        path = {node: [] for node in self._nodes}
        dist[source] = 0.0
        path[source] = [source]

        heap = [(0.0, source)]

        while heap:
            d, u = heapq.heappop(heap)

            if d > dist[u]:
                continue

            for v, w in self._adj[u]:
                if dist[u] + w < dist[v]:
                    dist[v] = dist[u] + w
                    path[v] = path[u] + [v]
                    heapq.heappush(heap, (dist[v], v))

        return dist, path

    def find_steiner_tree(self, terminals: Set[int]) -> SteinerResult:
        """
        Find Steiner tree using MST heuristic.

        Args:
            terminals: Set of terminal vertices

        Returns:
            SteinerResult
        """
        with self._lock:
            terminals = list(terminals)
            k = len(terminals)

            if k <= 1:
                return SteinerResult(is_optimal=True)

            # Compute shortest paths between all terminals
            all_dist = {}
            all_paths = {}

            for t in terminals:
                dist, paths = self._dijkstra_full(t)
                all_dist[t] = dist
                all_paths[t] = paths

            # Build complete graph on terminals
            terminal_edges = []
            for i, t1 in enumerate(terminals):
                for t2 in terminals[i+1:]:
                    if all_dist[t1][t2] < float('inf'):
                        terminal_edges.append((all_dist[t1][t2], t1, t2))

            terminal_edges.sort()

            # Kruskal's MST on terminal graph
            parent = {t: t for t in terminals}
            rank = {t: 0 for t in terminals}

            def find(x):
                if parent[x] != x:
                    parent[x] = find(parent[x])
                return parent[x]

            def union(x, y):
                px, py = find(x), find(y)
                if px == py:
                    return False
                if rank[px] < rank[py]:
                    px, py = py, px
                parent[py] = px
                if rank[px] == rank[py]:
                    rank[px] += 1
                return True

            mst_paths = []
            for d, t1, t2 in terminal_edges:
                if union(t1, t2):
                    mst_paths.append((t1, t2))

            # Collect all edges from paths
            tree_edges_set = set()
            tree_nodes = set()

            for t1, t2 in mst_paths:
                path = all_paths[t1][t2]

                for i in range(len(path) - 1):
                    u, v = path[i], path[i+1]
                    edge_key = (min(u, v), max(u, v))

                    if edge_key not in tree_edges_set:
                        tree_edges_set.add(edge_key)
                        tree_nodes.add(u)
                        tree_nodes.add(v)

            # Get edge weights
            tree_edges = []
            total_weight = 0.0

            for u, v in tree_edges_set:
                weight = None
                for neighbor, w in self._adj[u]:
                    if neighbor == v:
                        weight = w
                        break

                if weight is not None:
                    tree_edges.append((u, v, weight))
                    total_weight += weight

            steiner_vertices = tree_nodes - set(terminals)

            return SteinerResult(
                edges=tree_edges,
                steiner_vertices=steiner_vertices,
                total_weight=total_weight,
                is_optimal=False
            )


# ============================================================================
# STEINER TREE - DP (EXACT FOR SMALL K)
# ============================================================================

class DPSteiner:
    """
    Exact Steiner tree using DP.

    Dreyfus-Wagner algorithm: O(3^k * n + 2^k * n^2 + n^2 * log n)
    Suitable for small number of terminals (k ≤ 15).

    "Ba'el computes the true optimum." — Ba'el
    """

    def __init__(self):
        """Initialize DP Steiner."""
        self._adj: Dict[int, List[Tuple[int, float]]] = defaultdict(list)
        self._nodes: Set[int] = set()
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int, weight: float) -> None:
        """Add undirected weighted edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].append((v, weight))
            self._adj[v].append((u, weight))

    def find_steiner_tree(self, terminals: Set[int]) -> SteinerResult:
        """
        Find optimal Steiner tree.

        Args:
            terminals: Set of terminal vertices

        Returns:
            SteinerResult with optimal tree
        """
        with self._lock:
            terminals = list(terminals)
            k = len(terminals)
            n = len(self._nodes)

            if k <= 1:
                return SteinerResult(is_optimal=True)

            if k > 15:
                # Fall back to heuristic
                mst = MSTSteiner()
                for u in self._adj:
                    for v, w in self._adj[u]:
                        mst.add_edge(u, v, w)
                return mst.find_steiner_tree(set(terminals))

            nodes = list(self._nodes)
            node_idx = {node: i for i, node in enumerate(nodes)}
            term_idx = {t: i for i, t in enumerate(terminals)}

            INF = float('inf')

            # All pairs shortest paths
            dist = [[INF] * n for _ in range(n)]
            for i in range(n):
                dist[i][i] = 0

            for u in self._adj:
                ui = node_idx[u]
                for v, w in self._adj[u]:
                    vi = node_idx[v]
                    dist[ui][vi] = min(dist[ui][vi], w)

            # Floyd-Warshall
            for mid in range(n):
                for i in range(n):
                    for j in range(n):
                        if dist[i][mid] + dist[mid][j] < dist[i][j]:
                            dist[i][j] = dist[i][mid] + dist[mid][j]

            # DP: dp[mask][v] = min cost Steiner tree with terminals in mask, rooted at v
            dp = [[INF] * n for _ in range(1 << k)]

            # Base: single terminals
            for i, t in enumerate(terminals):
                ti = node_idx[t]
                dp[1 << i][ti] = 0

            # Fill DP
            for mask in range(1, 1 << k):
                # Combine smaller subsets
                sub = mask
                while sub > 0:
                    comp = mask ^ sub
                    if comp and sub < comp:  # Avoid duplicates
                        for v in range(n):
                            if dp[sub][v] + dp[comp][v] < dp[mask][v]:
                                dp[mask][v] = dp[sub][v] + dp[comp][v]
                    sub = (sub - 1) & mask

                # Relax using shortest paths
                for v in range(n):
                    for u in range(n):
                        if dp[mask][u] + dist[u][v] < dp[mask][v]:
                            dp[mask][v] = dp[mask][u] + dist[u][v]

            # Find optimal root
            full_mask = (1 << k) - 1
            opt_cost = min(dp[full_mask])

            return SteinerResult(
                total_weight=opt_cost,
                is_optimal=True
            )


# ============================================================================
# RECTILINEAR STEINER TREE
# ============================================================================

class RectilinearSteiner:
    """
    Rectilinear Steiner tree for 2D points.

    Uses Manhattan distance (L1 norm).

    "Ba'el connects on the grid." — Ba'el
    """

    def __init__(self):
        """Initialize rectilinear Steiner."""
        self._points: List[Tuple[int, int]] = []
        self._lock = threading.RLock()

    def add_point(self, x: int, y: int) -> None:
        """Add terminal point."""
        with self._lock:
            self._points.append((x, y))

    def find_steiner_tree(self) -> Tuple[List[Tuple[Tuple[int, int], Tuple[int, int]]], int]:
        """
        Find rectilinear Steiner tree.

        Uses Hanan grid approach with MST.

        Returns:
            (edges as point pairs, total Manhattan length)
        """
        with self._lock:
            if len(self._points) <= 1:
                return [], 0

            # Build Hanan grid
            xs = sorted(set(p[0] for p in self._points))
            ys = sorted(set(p[1] for p in self._points))

            hanan_points = [(x, y) for x in xs for y in ys]

            # Build graph on Hanan grid
            point_idx = {p: i for i, p in enumerate(hanan_points)}
            n = len(hanan_points)

            # Add edges between adjacent grid points
            edges = []
            for p in hanan_points:
                x, y = p
                pi = point_idx[p]

                # Right neighbor
                xi = xs.index(x)
                if xi + 1 < len(xs):
                    q = (xs[xi + 1], y)
                    if q in point_idx:
                        edges.append((pi, point_idx[q], abs(xs[xi + 1] - x)))

                # Up neighbor
                yi = ys.index(y)
                if yi + 1 < len(ys):
                    q = (x, ys[yi + 1])
                    if q in point_idx:
                        edges.append((pi, point_idx[q], abs(ys[yi + 1] - y)))

            # Find Steiner tree connecting terminal indices
            terminal_indices = set()
            for p in self._points:
                terminal_indices.add(point_idx[p])

            # Use shortest path Steiner on this grid graph
            sp_steiner = ShortestPathSteiner()

            for u, v, w in edges:
                sp_steiner.add_edge(u, v, float(w))

            for i in range(n):
                if i not in sp_steiner._nodes:
                    sp_steiner._nodes.add(i)

            result = sp_steiner.find_steiner_tree(terminal_indices)

            # Convert back to point coordinates
            point_edges = []
            for u, v, w in result.edges:
                p1 = hanan_points[u]
                p2 = hanan_points[v]
                point_edges.append((p1, p2))

            return point_edges, int(result.total_weight)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_shortest_path_steiner() -> ShortestPathSteiner:
    """Create shortest path Steiner engine."""
    return ShortestPathSteiner()


def create_mst_steiner() -> MSTSteiner:
    """Create MST Steiner engine."""
    return MSTSteiner()


def create_dp_steiner() -> DPSteiner:
    """Create DP Steiner engine."""
    return DPSteiner()


def create_rectilinear_steiner() -> RectilinearSteiner:
    """Create rectilinear Steiner engine."""
    return RectilinearSteiner()


def steiner_tree(
    edges: List[Tuple[int, int, float]],
    terminals: Set[int],
    exact: bool = False
) -> SteinerResult:
    """
    Find Steiner tree connecting terminals.

    Args:
        edges: List of (u, v, weight) edges
        terminals: Set of terminal vertices
        exact: Use exact DP (slower but optimal)

    Returns:
        SteinerResult
    """
    if exact:
        engine = DPSteiner()
    else:
        engine = MSTSteiner()

    for u, v, w in edges:
        engine.add_edge(u, v, w)

    return engine.find_steiner_tree(terminals)


def steiner_tree_weight(
    edges: List[Tuple[int, int, float]],
    terminals: Set[int]
) -> float:
    """Get Steiner tree total weight."""
    result = steiner_tree(edges, terminals)
    return result.total_weight


def rectilinear_steiner_tree(
    points: List[Tuple[int, int]]
) -> Tuple[List[Tuple[Tuple[int, int], Tuple[int, int]]], int]:
    """Find rectilinear Steiner tree for 2D points."""
    engine = RectilinearSteiner()
    for x, y in points:
        engine.add_point(x, y)
    return engine.find_steiner_tree()
