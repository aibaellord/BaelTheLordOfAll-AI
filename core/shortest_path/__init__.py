"""
BAEL Shortest Path Suite
========================

Comprehensive shortest path algorithms.

"Ba'el finds the optimal route." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import heapq

logger = logging.getLogger("BAEL.ShortestPath")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class PathResult:
    """Shortest path result."""
    distance: float
    path: List[int] = field(default_factory=list)
    exists: bool = True


@dataclass
class SPStats:
    """Shortest path statistics."""
    node_count: int = 0
    edge_count: int = 0
    relaxations: int = 0
    has_negative_cycle: bool = False


# ============================================================================
# DIJKSTRA'S ALGORITHM
# ============================================================================

class Dijkstra:
    """
    Dijkstra's algorithm for single-source shortest paths.

    Features:
    - O((V + E) log V) with binary heap
    - Non-negative edge weights only
    - Path reconstruction

    "Ba'el explores greedily." — Ba'el
    """

    def __init__(self):
        """Initialize Dijkstra."""
        self._adj: Dict[int, List[Tuple[int, float]]] = defaultdict(list)
        self._nodes: Set[int] = set()
        self._edge_count = 0
        self._lock = threading.RLock()

        logger.debug("Dijkstra initialized")

    def add_edge(self, u: int, v: int, weight: float) -> None:
        """Add directed edge u → v with weight."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].append((v, weight))
            self._edge_count += 1

    def add_undirected_edge(self, u: int, v: int, weight: float) -> None:
        """Add undirected edge."""
        self.add_edge(u, v, weight)
        self.add_edge(v, u, weight)

    def shortest_path(self, source: int, target: int) -> PathResult:
        """
        Find shortest path from source to target.

        Returns:
            PathResult with distance and path
        """
        with self._lock:
            dist = {node: float('inf') for node in self._nodes}
            dist[source] = 0
            prev = {}

            heap = [(0, source)]
            visited = set()

            while heap:
                d, u = heapq.heappop(heap)

                if u in visited:
                    continue
                visited.add(u)

                if u == target:
                    break

                for v, w in self._adj[u]:
                    if dist[u] + w < dist[v]:
                        dist[v] = dist[u] + w
                        prev[v] = u
                        heapq.heappush(heap, (dist[v], v))

            if dist[target] == float('inf'):
                return PathResult(distance=float('inf'), path=[], exists=False)

            # Reconstruct path
            path = []
            current = target
            while current in prev:
                path.append(current)
                current = prev[current]
            path.append(source)
            path.reverse()

            return PathResult(distance=dist[target], path=path, exists=True)

    def all_shortest_paths(self, source: int) -> Dict[int, float]:
        """
        Find shortest paths from source to all nodes.

        Returns:
            Dict mapping node → distance
        """
        with self._lock:
            dist = {node: float('inf') for node in self._nodes}
            dist[source] = 0

            heap = [(0, source)]
            visited = set()

            while heap:
                d, u = heapq.heappop(heap)

                if u in visited:
                    continue
                visited.add(u)

                for v, w in self._adj[u]:
                    if dist[u] + w < dist[v]:
                        dist[v] = dist[u] + w
                        heapq.heappush(heap, (dist[v], v))

            return dist


# ============================================================================
# BELLMAN-FORD ALGORITHM
# ============================================================================

class BellmanFord:
    """
    Bellman-Ford algorithm for single-source shortest paths.

    Features:
    - O(VE) complexity
    - Handles negative edge weights
    - Detects negative cycles

    "Ba'el relaxes systematically." — Ba'el
    """

    def __init__(self):
        """Initialize Bellman-Ford."""
        self._edges: List[Tuple[int, int, float]] = []
        self._nodes: Set[int] = set()
        self._stats = SPStats()
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int, weight: float) -> None:
        """Add directed edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._edges.append((u, v, weight))

    def shortest_path(self, source: int) -> Tuple[Dict[int, float], Dict[int, int], bool]:
        """
        Find shortest paths from source.

        Returns:
            (distances, predecessors, has_negative_cycle)
        """
        with self._lock:
            dist = {node: float('inf') for node in self._nodes}
            dist[source] = 0
            prev = {}

            n = len(self._nodes)
            relaxations = 0

            # Relax n-1 times
            for _ in range(n - 1):
                updated = False

                for u, v, w in self._edges:
                    if dist[u] != float('inf') and dist[u] + w < dist[v]:
                        dist[v] = dist[u] + w
                        prev[v] = u
                        updated = True
                        relaxations += 1

                if not updated:
                    break

            # Check for negative cycle
            has_negative_cycle = False
            for u, v, w in self._edges:
                if dist[u] != float('inf') and dist[u] + w < dist[v]:
                    has_negative_cycle = True
                    break

            self._stats.node_count = n
            self._stats.edge_count = len(self._edges)
            self._stats.relaxations = relaxations
            self._stats.has_negative_cycle = has_negative_cycle

            return dist, prev, has_negative_cycle

    def find_negative_cycle(self) -> Optional[List[int]]:
        """
        Find and return a negative cycle if one exists.

        Returns:
            List of nodes in cycle, or None
        """
        with self._lock:
            if not self._nodes:
                return None

            source = next(iter(self._nodes))
            dist = {node: float('inf') for node in self._nodes}
            dist[source] = 0
            prev = {}

            n = len(self._nodes)

            # Relax n-1 times
            for _ in range(n - 1):
                for u, v, w in self._edges:
                    if dist[u] != float('inf') and dist[u] + w < dist[v]:
                        dist[v] = dist[u] + w
                        prev[v] = u

            # Find negative cycle edge
            cycle_node = None
            for u, v, w in self._edges:
                if dist[u] != float('inf') and dist[u] + w < dist[v]:
                    cycle_node = v
                    prev[v] = u
                    break

            if cycle_node is None:
                return None

            # Trace back n times to ensure we're in the cycle
            for _ in range(n):
                cycle_node = prev.get(cycle_node, cycle_node)

            # Extract cycle
            cycle = []
            current = cycle_node
            while True:
                cycle.append(current)
                current = prev.get(current)
                if current == cycle_node:
                    cycle.append(current)
                    break

            cycle.reverse()
            return cycle

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'node_count': self._stats.node_count,
            'edge_count': self._stats.edge_count,
            'relaxations': self._stats.relaxations,
            'has_negative_cycle': self._stats.has_negative_cycle
        }


# ============================================================================
# FLOYD-WARSHALL ALGORITHM
# ============================================================================

class FloydWarshall:
    """
    Floyd-Warshall algorithm for all-pairs shortest paths.

    Features:
    - O(V³) complexity
    - Handles negative weights
    - Detects negative cycles

    "Ba'el computes all paths at once." — Ba'el
    """

    def __init__(self):
        """Initialize Floyd-Warshall."""
        self._adj: Dict[int, Dict[int, float]] = defaultdict(lambda: defaultdict(lambda: float('inf')))
        self._nodes: Set[int] = set()
        self._dist: Optional[Dict[int, Dict[int, float]]] = None
        self._next: Optional[Dict[int, Dict[int, int]]] = None
        self._has_negative_cycle = False
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int, weight: float) -> None:
        """Add directed edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u][v] = min(self._adj[u][v], weight)
            self._dist = None  # Invalidate cache

    def solve(self) -> bool:
        """
        Compute all-pairs shortest paths.

        Returns:
            True if no negative cycle, False otherwise
        """
        with self._lock:
            if self._dist is not None:
                return not self._has_negative_cycle

            nodes = list(self._nodes)
            n = len(nodes)
            idx = {node: i for i, node in enumerate(nodes)}

            # Initialize
            dist = [[float('inf')] * n for _ in range(n)]
            next_node = [[None] * n for _ in range(n)]

            for i in range(n):
                dist[i][i] = 0

            for u in self._adj:
                for v, w in self._adj[u].items():
                    i, j = idx[u], idx[v]
                    if w < dist[i][j]:
                        dist[i][j] = w
                        next_node[i][j] = j

            # Floyd-Warshall
            for k in range(n):
                for i in range(n):
                    for j in range(n):
                        if dist[i][k] != float('inf') and dist[k][j] != float('inf'):
                            if dist[i][k] + dist[k][j] < dist[i][j]:
                                dist[i][j] = dist[i][k] + dist[k][j]
                                next_node[i][j] = next_node[i][k]

            # Check for negative cycles
            self._has_negative_cycle = any(dist[i][i] < 0 for i in range(n))

            # Convert to dict
            self._dist = {}
            self._next = {}

            for i, u in enumerate(nodes):
                self._dist[u] = {}
                self._next[u] = {}
                for j, v in enumerate(nodes):
                    self._dist[u][v] = dist[i][j]
                    self._next[u][v] = nodes[next_node[i][j]] if next_node[i][j] is not None else None

            return not self._has_negative_cycle

    def distance(self, u: int, v: int) -> float:
        """Get shortest distance from u to v."""
        self.solve()
        return self._dist.get(u, {}).get(v, float('inf'))

    def path(self, u: int, v: int) -> List[int]:
        """Get shortest path from u to v."""
        self.solve()

        if self._dist.get(u, {}).get(v, float('inf')) == float('inf'):
            return []

        path = [u]
        while u != v:
            u = self._next[u][v]
            if u is None:
                return []
            path.append(u)

        return path

    def has_negative_cycle(self) -> bool:
        """Check if graph has negative cycle."""
        self.solve()
        return self._has_negative_cycle


# ============================================================================
# JOHNSON'S ALGORITHM
# ============================================================================

class Johnson:
    """
    Johnson's algorithm for all-pairs shortest paths.

    Features:
    - O(V² log V + VE) complexity
    - Better than Floyd-Warshall for sparse graphs
    - Uses Bellman-Ford + Dijkstra

    "Ba'el reweights and conquers." — Ba'el
    """

    def __init__(self):
        """Initialize Johnson's algorithm."""
        self._adj: Dict[int, List[Tuple[int, float]]] = defaultdict(list)
        self._nodes: Set[int] = set()
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int, weight: float) -> None:
        """Add directed edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].append((v, weight))

    def solve(self) -> Tuple[Optional[Dict[int, Dict[int, float]]], bool]:
        """
        Compute all-pairs shortest paths.

        Returns:
            (distance_matrix, has_negative_cycle)
        """
        with self._lock:
            # Add virtual source connected to all nodes with weight 0
            virtual = object()  # Unique ID

            bf = BellmanFord()

            for node in self._nodes:
                bf.add_edge(virtual, node, 0)

            for u in self._adj:
                for v, w in self._adj[u]:
                    bf.add_edge(u, v, w)

            h, _, has_neg = bf.shortest_path(virtual)

            if has_neg:
                return None, True

            # Reweight edges
            reweighted = defaultdict(list)

            for u in self._adj:
                for v, w in self._adj[u]:
                    new_weight = w + h[u] - h[v]
                    reweighted[u].append((v, new_weight))

            # Run Dijkstra from each source
            result = {}

            for source in self._nodes:
                dijkstra = Dijkstra()

                for u in reweighted:
                    for v, w in reweighted[u]:
                        dijkstra.add_edge(u, v, w)

                dist = dijkstra.all_shortest_paths(source)

                # Convert back to original weights
                result[source] = {}
                for target in self._nodes:
                    if dist[target] == float('inf'):
                        result[source][target] = float('inf')
                    else:
                        result[source][target] = dist[target] - h[source] + h[target]

            return result, False


# ============================================================================
# SPFA (Shortest Path Faster Algorithm)
# ============================================================================

class SPFA:
    """
    SPFA - Bellman-Ford optimization.

    Features:
    - O(VE) worst case, often faster
    - Handles negative weights
    - Queue-based relaxation

    "Ba'el relaxes only when needed." — Ba'el
    """

    def __init__(self):
        """Initialize SPFA."""
        self._adj: Dict[int, List[Tuple[int, float]]] = defaultdict(list)
        self._nodes: Set[int] = set()
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int, weight: float) -> None:
        """Add directed edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].append((v, weight))

    def shortest_path(self, source: int) -> Tuple[Dict[int, float], bool]:
        """
        Find shortest paths from source.

        Returns:
            (distances, has_negative_cycle)
        """
        with self._lock:
            from collections import deque

            dist = {node: float('inf') for node in self._nodes}
            dist[source] = 0

            in_queue = {node: False for node in self._nodes}
            in_queue[source] = True

            count = {node: 0 for node in self._nodes}
            count[source] = 1

            queue = deque([source])
            n = len(self._nodes)

            while queue:
                u = queue.popleft()
                in_queue[u] = False

                for v, w in self._adj[u]:
                    if dist[u] + w < dist[v]:
                        dist[v] = dist[u] + w

                        if not in_queue[v]:
                            queue.append(v)
                            in_queue[v] = True
                            count[v] += 1

                            if count[v] > n:
                                # Negative cycle
                                return dist, True

            return dist, False


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_dijkstra() -> Dijkstra:
    """Create Dijkstra engine."""
    return Dijkstra()


def create_bellman_ford() -> BellmanFord:
    """Create Bellman-Ford engine."""
    return BellmanFord()


def create_floyd_warshall() -> FloydWarshall:
    """Create Floyd-Warshall engine."""
    return FloydWarshall()


def create_johnson() -> Johnson:
    """Create Johnson's algorithm engine."""
    return Johnson()


def create_spfa() -> SPFA:
    """Create SPFA engine."""
    return SPFA()


def shortest_path(
    edges: List[Tuple[int, int, float]],
    source: int,
    target: int
) -> PathResult:
    """Find shortest path using Dijkstra."""
    engine = Dijkstra()
    for u, v, w in edges:
        engine.add_edge(u, v, w)
    return engine.shortest_path(source, target)


def all_pairs_shortest_paths(
    edges: List[Tuple[int, int, float]],
    algorithm: str = "floyd"
) -> Dict[int, Dict[int, float]]:
    """
    Compute all-pairs shortest paths.

    Args:
        edges: List of (u, v, weight)
        algorithm: "floyd" or "johnson"

    Returns:
        Dict[u][v] = distance from u to v
    """
    if algorithm == "johnson":
        engine = Johnson()
        for u, v, w in edges:
            engine.add_edge(u, v, w)
        result, _ = engine.solve()
        return result or {}
    else:
        engine = FloydWarshall()
        for u, v, w in edges:
            engine.add_edge(u, v, w)
        engine.solve()
        return engine._dist or {}


def has_negative_cycle(edges: List[Tuple[int, int, float]]) -> bool:
    """Check if graph has negative cycle."""
    if not edges:
        return False

    engine = BellmanFord()
    for u, v, w in edges:
        engine.add_edge(u, v, w)

    source = edges[0][0]
    _, _, has_neg = engine.shortest_path(source)
    return has_neg
