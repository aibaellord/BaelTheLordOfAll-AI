"""
BAEL Global Minimum Cut Engine
==============================

Minimum cut algorithms for undirected graphs.

"Ba'el finds the weakest link." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import heapq

logger = logging.getLogger("BAEL.MinCut")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class MinCutStats:
    """Minimum cut statistics."""
    node_count: int = 0
    edge_count: int = 0
    cut_value: float = 0.0
    iterations: int = 0


# ============================================================================
# STOER-WAGNER ALGORITHM
# ============================================================================

class StoerWagner:
    """
    Stoer-Wagner algorithm for global minimum cut.

    Features:
    - O(VE + V² log V) complexity
    - Works for undirected weighted graphs
    - No source/sink required

    "Ba'el finds the minimum separator." — Ba'el
    """

    def __init__(self):
        """Initialize Stoer-Wagner."""
        self._adj: Dict[int, Dict[int, float]] = defaultdict(lambda: defaultdict(float))
        self._nodes: Set[int] = set()
        self._edge_count = 0
        self._stats = MinCutStats()
        self._built = False
        self._cut_value = float('inf')
        self._cut_partition: Tuple[Set[int], Set[int]] = (set(), set())
        self._lock = threading.RLock()

        logger.debug("Stoer-Wagner initialized")

    def add_edge(self, u: int, v: int, weight: float = 1.0) -> None:
        """Add undirected weighted edge."""
        with self._lock:
            self._built = False
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u][v] += weight
            self._adj[v][u] += weight
            self._edge_count += 1

    def _minimum_cut_phase(
        self,
        adj: Dict[int, Dict[int, float]],
        nodes: Set[int]
    ) -> Tuple[int, int, float]:
        """
        Single phase of Stoer-Wagner.

        Returns:
            (s, t, cut_of_the_phase)
        """
        # Maximum adjacency search
        A = set()
        start = next(iter(nodes))

        weights = {v: 0.0 for v in nodes}

        for v, w in adj[start].items():
            if v in nodes:
                weights[v] = w

        A.add(start)
        prev_added = start
        last_added = start
        cut_of_phase = 0.0

        # Priority queue (max-heap using negative)
        heap = [(-weights[v], v) for v in nodes if v != start]
        heapq.heapify(heap)

        while len(A) < len(nodes):
            # Find most tightly connected vertex
            while heap:
                neg_w, v = heapq.heappop(heap)
                if v not in A and weights[v] == -neg_w:
                    break
            else:
                # Find manually
                max_w = -float('inf')
                v = None
                for u in nodes:
                    if u not in A and weights[u] > max_w:
                        max_w = weights[u]
                        v = u
                if v is None:
                    break

            A.add(v)
            prev_added = last_added
            last_added = v
            cut_of_phase = weights[v]

            # Update weights
            for u, w in adj[v].items():
                if u in nodes and u not in A:
                    weights[u] += w
                    heapq.heappush(heap, (-weights[u], u))

        return prev_added, last_added, cut_of_phase

    def solve(self) -> float:
        """
        Find global minimum cut.

        Returns:
            Minimum cut value
        """
        with self._lock:
            if self._built:
                return self._cut_value

            if len(self._nodes) < 2:
                self._cut_value = 0.0
                self._built = True
                return 0.0

            # Copy graph for modification
            adj = defaultdict(lambda: defaultdict(float))
            for u in self._adj:
                for v, w in self._adj[u].items():
                    adj[u][v] = w

            nodes = set(self._nodes)

            # Track merged vertices
            merged = {v: {v} for v in nodes}

            min_cut = float('inf')
            min_cut_side = set()
            iterations = 0

            while len(nodes) > 1:
                s, t, cut_of_phase = self._minimum_cut_phase(adj, nodes)

                if cut_of_phase < min_cut:
                    min_cut = cut_of_phase
                    min_cut_side = merged[t].copy()

                # Merge t into s
                merged[s] |= merged[t]

                for v, w in adj[t].items():
                    if v != s and v in nodes:
                        adj[s][v] += w
                        adj[v][s] += w

                # Remove t
                for v in list(adj[t].keys()):
                    del adj[v][t]
                del adj[t]
                nodes.remove(t)

                iterations += 1

            self._cut_value = min_cut
            self._cut_partition = (min_cut_side, self._nodes - min_cut_side)

            self._stats.node_count = len(self._nodes)
            self._stats.edge_count = self._edge_count
            self._stats.cut_value = min_cut
            self._stats.iterations = iterations

            self._built = True

            logger.info(f"Stoer-Wagner min cut: {min_cut}")
            return min_cut

    def get_partition(self) -> Tuple[Set[int], Set[int]]:
        """Get the minimum cut partition."""
        self.solve()
        return self._cut_partition

    def get_cut_edges(self) -> List[Tuple[int, int, float]]:
        """Get edges crossing the minimum cut."""
        self.solve()
        s_side, t_side = self._cut_partition

        cut_edges = []
        for u in s_side:
            for v, w in self._adj[u].items():
                if v in t_side:
                    cut_edges.append((u, v, w))

        return cut_edges

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        self.solve()
        return {
            'node_count': self._stats.node_count,
            'edge_count': self._stats.edge_count,
            'cut_value': self._stats.cut_value,
            'iterations': self._stats.iterations
        }


# ============================================================================
# KARGER'S RANDOMIZED ALGORITHM
# ============================================================================

class KargerMinCut:
    """
    Karger's randomized algorithm for minimum cut.

    Features:
    - O(n²) per iteration
    - High probability with O(n² log n) iterations
    - Simple contraction approach

    "Ba'el contracts randomly to find the cut." — Ba'el
    """

    def __init__(self):
        """Initialize Karger's algorithm."""
        self._edges: List[Tuple[int, int, float]] = []
        self._nodes: Set[int] = set()
        self._stats = MinCutStats()
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int, weight: float = 1.0) -> None:
        """Add undirected weighted edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._edges.append((u, v, weight))

    def _contract_once(self) -> float:
        """Single contraction run."""
        import random

        # Union-Find
        parent = {v: v for v in self._nodes}
        rank = {v: 0 for v in self._nodes}

        def find(x: int) -> int:
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x: int, y: int) -> None:
            px, py = find(x), find(y)
            if px == py:
                return
            if rank[px] < rank[py]:
                px, py = py, px
            parent[py] = px
            if rank[px] == rank[py]:
                rank[px] += 1

        # Copy edges with weights
        edges = [(u, v, w) for u, v, w in self._edges]

        components = len(self._nodes)

        while components > 2:
            # Select random edge weighted by weight
            total_weight = sum(w for _, _, w in edges
                              if find(edges[0][0]) != find(edges[0][1])
                              for _ in [None])

            # Actually, for simplicity, just pick uniformly
            valid_edges = [(u, v, w) for u, v, w in edges if find(u) != find(v)]

            if not valid_edges:
                break

            # Weight-based selection
            total = sum(w for _, _, w in valid_edges)
            r = random.uniform(0, total)

            cumsum = 0
            for u, v, w in valid_edges:
                cumsum += w
                if cumsum >= r:
                    union(u, v)
                    components -= 1
                    break

        # Count cut weight
        cut_weight = sum(w for u, v, w in self._edges if find(u) != find(v))
        return cut_weight

    def solve(self, iterations: Optional[int] = None) -> float:
        """
        Find minimum cut using randomized contractions.

        Args:
            iterations: Number of iterations (default: n² log n)

        Returns:
            Best minimum cut found
        """
        with self._lock:
            import math

            n = len(self._nodes)

            if n < 2:
                return 0.0

            if iterations is None:
                iterations = max(1, int(n * n * math.log(n + 1)))

            min_cut = float('inf')

            for i in range(iterations):
                cut = self._contract_once()
                min_cut = min(min_cut, cut)

            self._stats.node_count = n
            self._stats.edge_count = len(self._edges)
            self._stats.cut_value = min_cut
            self._stats.iterations = iterations

            logger.info(f"Karger min cut: {min_cut}")
            return min_cut


# ============================================================================
# KARGER-STEIN ALGORITHM
# ============================================================================

class KargerSteinMinCut:
    """
    Karger-Stein algorithm for minimum cut.

    Features:
    - O(n² log³ n) expected time
    - Recursive contraction
    - Better probability than basic Karger

    "Ba'el divides and conquers the cut." — Ba'el
    """

    def __init__(self):
        """Initialize Karger-Stein."""
        self._adj: Dict[int, Dict[int, float]] = defaultdict(lambda: defaultdict(float))
        self._nodes: Set[int] = set()
        self._stats = MinCutStats()
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int, weight: float = 1.0) -> None:
        """Add undirected weighted edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u][v] += weight
            self._adj[v][u] += weight

    def _contract(
        self,
        adj: Dict[int, Dict[int, float]],
        nodes: Set[int],
        target: int
    ) -> Tuple[Dict[int, Dict[int, float]], Set[int]]:
        """Contract graph to target number of vertices."""
        import random

        adj = {u: dict(neighbors) for u, neighbors in adj.items() if u in nodes}
        nodes = set(nodes)

        while len(nodes) > target:
            # Build edge list
            edges = []
            for u in nodes:
                for v, w in adj[u].items():
                    if u < v and v in nodes:
                        edges.append((u, v, w))

            if not edges:
                break

            # Random edge
            total = sum(w for _, _, w in edges)
            r = random.uniform(0, total)

            cumsum = 0
            u, v = edges[0][0], edges[0][1]
            for eu, ev, w in edges:
                cumsum += w
                if cumsum >= r:
                    u, v = eu, ev
                    break

            # Merge v into u
            for x, w in adj[v].items():
                if x != u and x in nodes:
                    adj[u][x] = adj[u].get(x, 0) + w
                    adj[x][u] = adj[x].get(u, 0) + w
                    if v in adj[x]:
                        del adj[x][v]

            del adj[v]
            nodes.remove(v)

        return adj, nodes

    def _karger_stein(
        self,
        adj: Dict[int, Dict[int, float]],
        nodes: Set[int]
    ) -> float:
        """Recursive Karger-Stein."""
        import math

        n = len(nodes)

        if n <= 6:
            # Base case: use Stoer-Wagner
            sw = StoerWagner()
            for u in nodes:
                for v, w in adj[u].items():
                    if u < v and v in nodes:
                        sw.add_edge(u, v, w)
            return sw.solve()

        t = int(math.ceil(1 + n / math.sqrt(2)))

        # Two independent contractions
        adj1, nodes1 = self._contract(adj, nodes, t)
        adj2, nodes2 = self._contract(adj, nodes, t)

        return min(
            self._karger_stein(adj1, nodes1),
            self._karger_stein(adj2, nodes2)
        )

    def solve(self, iterations: int = 1) -> float:
        """
        Find minimum cut.

        Args:
            iterations: Number of full runs

        Returns:
            Minimum cut value
        """
        with self._lock:
            if len(self._nodes) < 2:
                return 0.0

            min_cut = float('inf')

            for _ in range(iterations):
                cut = self._karger_stein(self._adj, self._nodes)
                min_cut = min(min_cut, cut)

            self._stats.node_count = len(self._nodes)
            self._stats.cut_value = min_cut
            self._stats.iterations = iterations

            return min_cut


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_stoer_wagner() -> StoerWagner:
    """Create Stoer-Wagner engine."""
    return StoerWagner()


def create_karger() -> KargerMinCut:
    """Create Karger min-cut engine."""
    return KargerMinCut()


def create_karger_stein() -> KargerSteinMinCut:
    """Create Karger-Stein engine."""
    return KargerSteinMinCut()


def global_min_cut(
    edges: List[Tuple[int, int, float]],
    algorithm: str = "stoer_wagner"
) -> float:
    """
    Find global minimum cut in undirected graph.

    Args:
        edges: List of (u, v, weight) undirected edges
        algorithm: "stoer_wagner", "karger", or "karger_stein"

    Returns:
        Minimum cut value
    """
    if algorithm == "karger":
        engine = KargerMinCut()
    elif algorithm == "karger_stein":
        engine = KargerSteinMinCut()
    else:
        engine = StoerWagner()

    for u, v, w in edges:
        engine.add_edge(u, v, w)

    return engine.solve()


def min_cut_partition(
    edges: List[Tuple[int, int, float]]
) -> Tuple[Set[int], Set[int]]:
    """Get minimum cut partition."""
    engine = StoerWagner()
    for u, v, w in edges:
        engine.add_edge(u, v, w)
    return engine.get_partition()


def is_k_edge_connected(
    edges: List[Tuple[int, int]],
    k: int
) -> bool:
    """Check if graph is k-edge-connected."""
    weighted = [(u, v, 1.0) for u, v in edges]
    cut = global_min_cut(weighted)
    return cut >= k
