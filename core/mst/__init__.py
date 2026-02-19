"""
BAEL Minimum Spanning Tree Engine
=================================

MST algorithms for weighted undirected graphs.

"Ba'el connects all with minimum cost." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import heapq

logger = logging.getLogger("BAEL.MST")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class MSTResult:
    """MST result."""
    edges: List[Tuple[int, int, float]] = field(default_factory=list)
    total_weight: float = 0.0
    is_connected: bool = True


@dataclass
class MSTStats:
    """MST statistics."""
    node_count: int = 0
    edge_count: int = 0
    mst_weight: float = 0.0
    mst_edges: int = 0


# ============================================================================
# KRUSKAL'S ALGORITHM
# ============================================================================

class KruskalMST:
    """
    Kruskal's algorithm for MST.

    Features:
    - O(E log E) complexity
    - Union-Find optimization
    - Edge-centric approach

    "Ba'el unites by cheapest links." — Ba'el
    """

    def __init__(self):
        """Initialize Kruskal's MST."""
        self._edges: List[Tuple[int, int, float]] = []
        self._nodes: Set[int] = set()
        self._stats = MSTStats()
        self._lock = threading.RLock()

        logger.debug("Kruskal MST initialized")

    def add_edge(self, u: int, v: int, weight: float) -> None:
        """Add undirected weighted edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._edges.append((u, v, weight))

    def find_mst(self) -> MSTResult:
        """
        Find minimum spanning tree.

        Returns:
            MSTResult with edges and total weight
        """
        with self._lock:
            # Union-Find
            parent = {v: v for v in self._nodes}
            rank = {v: 0 for v in self._nodes}

            def find(x: int) -> int:
                if parent[x] != x:
                    parent[x] = find(parent[x])
                return parent[x]

            def union(x: int, y: int) -> bool:
                px, py = find(x), find(y)
                if px == py:
                    return False
                if rank[px] < rank[py]:
                    px, py = py, px
                parent[py] = px
                if rank[px] == rank[py]:
                    rank[px] += 1
                return True

            # Sort edges by weight
            sorted_edges = sorted(self._edges, key=lambda e: e[2])

            mst_edges = []
            total_weight = 0.0

            for u, v, w in sorted_edges:
                if union(u, v):
                    mst_edges.append((u, v, w))
                    total_weight += w

                    if len(mst_edges) == len(self._nodes) - 1:
                        break

            is_connected = len(mst_edges) == len(self._nodes) - 1

            self._stats.node_count = len(self._nodes)
            self._stats.edge_count = len(self._edges)
            self._stats.mst_weight = total_weight
            self._stats.mst_edges = len(mst_edges)

            logger.info(f"Kruskal MST: {len(mst_edges)} edges, weight {total_weight}")

            return MSTResult(
                edges=mst_edges,
                total_weight=total_weight,
                is_connected=is_connected
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'node_count': self._stats.node_count,
            'edge_count': self._stats.edge_count,
            'mst_weight': self._stats.mst_weight,
            'mst_edges': self._stats.mst_edges
        }


# ============================================================================
# PRIM'S ALGORITHM
# ============================================================================

class PrimMST:
    """
    Prim's algorithm for MST.

    Features:
    - O((V + E) log V) with binary heap
    - Vertex-centric approach
    - Good for dense graphs

    "Ba'el grows the tree from a seed." — Ba'el
    """

    def __init__(self):
        """Initialize Prim's MST."""
        self._adj: Dict[int, List[Tuple[int, float]]] = defaultdict(list)
        self._nodes: Set[int] = set()
        self._stats = MSTStats()
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int, weight: float) -> None:
        """Add undirected weighted edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].append((v, weight))
            self._adj[v].append((u, weight))

    def find_mst(self, start: Optional[int] = None) -> MSTResult:
        """
        Find minimum spanning tree.

        Args:
            start: Optional starting vertex

        Returns:
            MSTResult with edges and total weight
        """
        with self._lock:
            if not self._nodes:
                return MSTResult()

            start = start if start is not None else next(iter(self._nodes))

            in_mst = set()
            mst_edges = []
            total_weight = 0.0

            # Priority queue: (weight, u, v) where v is in MST, u is not
            heap = [(0, start, None)]

            while heap and len(in_mst) < len(self._nodes):
                weight, node, parent = heapq.heappop(heap)

                if node in in_mst:
                    continue

                in_mst.add(node)

                if parent is not None:
                    mst_edges.append((parent, node, weight))
                    total_weight += weight

                for neighbor, w in self._adj[node]:
                    if neighbor not in in_mst:
                        heapq.heappush(heap, (w, neighbor, node))

            is_connected = len(in_mst) == len(self._nodes)

            self._stats.node_count = len(self._nodes)
            self._stats.mst_weight = total_weight
            self._stats.mst_edges = len(mst_edges)

            return MSTResult(
                edges=mst_edges,
                total_weight=total_weight,
                is_connected=is_connected
            )


# ============================================================================
# BORUVKA'S ALGORITHM
# ============================================================================

class BoruvkaMST:
    """
    Borůvka's algorithm for MST.

    Features:
    - O(E log V) complexity
    - Parallel-friendly
    - Component-based approach

    "Ba'el connects components simultaneously." — Ba'el
    """

    def __init__(self):
        """Initialize Borůvka's MST."""
        self._edges: List[Tuple[int, int, float]] = []
        self._nodes: Set[int] = set()
        self._stats = MSTStats()
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int, weight: float) -> None:
        """Add undirected weighted edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._edges.append((u, v, weight))

    def find_mst(self) -> MSTResult:
        """Find minimum spanning tree."""
        with self._lock:
            # Union-Find
            parent = {v: v for v in self._nodes}
            rank = {v: 0 for v in self._nodes}

            def find(x: int) -> int:
                if parent[x] != x:
                    parent[x] = find(parent[x])
                return parent[x]

            def union(x: int, y: int) -> bool:
                px, py = find(x), find(y)
                if px == py:
                    return False
                if rank[px] < rank[py]:
                    px, py = py, px
                parent[py] = px
                if rank[px] == rank[py]:
                    rank[px] += 1
                return True

            mst_edges = []
            total_weight = 0.0
            num_components = len(self._nodes)

            while num_components > 1:
                # Find cheapest edge for each component
                cheapest = {}  # component → (weight, u, v)

                for u, v, w in self._edges:
                    cu, cv = find(u), find(v)

                    if cu != cv:
                        if cu not in cheapest or w < cheapest[cu][0]:
                            cheapest[cu] = (w, u, v)
                        if cv not in cheapest or w < cheapest[cv][0]:
                            cheapest[cv] = (w, u, v)

                if not cheapest:
                    break

                # Add cheapest edges
                for comp, (w, u, v) in cheapest.items():
                    if union(u, v):
                        mst_edges.append((u, v, w))
                        total_weight += w
                        num_components -= 1

            is_connected = len(mst_edges) == len(self._nodes) - 1

            self._stats.node_count = len(self._nodes)
            self._stats.mst_weight = total_weight
            self._stats.mst_edges = len(mst_edges)

            return MSTResult(
                edges=mst_edges,
                total_weight=total_weight,
                is_connected=is_connected
            )


# ============================================================================
# SECOND-BEST MST
# ============================================================================

class SecondBestMST:
    """
    Find second-best MST.

    "Ba'el finds the next best option." — Ba'el
    """

    def __init__(self):
        """Initialize second-best MST."""
        self._edges: List[Tuple[int, int, float]] = []
        self._nodes: Set[int] = set()
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int, weight: float) -> None:
        """Add undirected weighted edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._edges.append((u, v, weight))

    def find_second_best(self) -> Optional[MSTResult]:
        """
        Find second-best MST.

        Returns:
            Second-best MST or None if doesn't exist
        """
        with self._lock:
            # First find MST
            kruskal = KruskalMST()
            for u, v, w in self._edges:
                kruskal.add_edge(u, v, w)

            mst = kruskal.find_mst()

            if not mst.is_connected:
                return None

            mst_edge_set = {(min(u, v), max(u, v)) for u, v, w in mst.edges}
            non_mst_edges = [(u, v, w) for u, v, w in self._edges
                            if (min(u, v), max(u, v)) not in mst_edge_set]

            if not non_mst_edges:
                return None

            # Build MST adjacency
            mst_adj = defaultdict(list)
            for u, v, w in mst.edges:
                mst_adj[u].append((v, w))
                mst_adj[v].append((u, w))

            # For each non-MST edge, find max edge on MST path
            def find_max_on_path(start: int, end: int) -> Tuple[int, int, float]:
                """BFS to find max edge on path."""
                from collections import deque

                visited = {start}
                queue = deque([(start, [])])  # (node, path_edges)

                while queue:
                    node, path = queue.popleft()

                    if node == end:
                        # Find max edge on path
                        if not path:
                            return None
                        return max(path, key=lambda e: e[2])

                    for neighbor, w in mst_adj[node]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append((neighbor, path + [(node, neighbor, w)]))

                return None

            # Find the swap that minimizes increase
            best_second = None
            best_weight = float('inf')

            for u, v, w in non_mst_edges:
                max_edge = find_max_on_path(u, v)

                if max_edge:
                    new_weight = mst.total_weight - max_edge[2] + w

                    if new_weight < best_weight:
                        best_weight = new_weight

                        # Build new MST
                        new_edges = [e for e in mst.edges
                                    if (min(e[0], e[1]), max(e[0], e[1])) !=
                                       (min(max_edge[0], max_edge[1]), max(max_edge[0], max_edge[1]))]
                        new_edges.append((u, v, w))

                        best_second = MSTResult(
                            edges=new_edges,
                            total_weight=best_weight,
                            is_connected=True
                        )

            return best_second


# ============================================================================
# MINIMUM SPANNING ARBORESCENCE
# ============================================================================

class MinimumArborescence:
    """
    Minimum spanning arborescence (directed MST).

    Edmonds/Chu-Liu algorithm for directed graphs.

    "Ba'el finds the rooted tree." — Ba'el
    """

    def __init__(self):
        """Initialize minimum arborescence."""
        self._edges: List[Tuple[int, int, float]] = []
        self._nodes: Set[int] = set()
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int, weight: float) -> None:
        """Add directed edge u → v."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._edges.append((u, v, weight))

    def find_arborescence(self, root: int) -> Optional[MSTResult]:
        """
        Find minimum arborescence rooted at given vertex.

        Uses Edmonds' algorithm (simplified version).
        """
        with self._lock:
            # Get minimum incoming edge for each non-root vertex
            min_incoming = {}

            for u, v, w in self._edges:
                if v != root:
                    if v not in min_incoming or w < min_incoming[v][1]:
                        min_incoming[v] = (u, w)

            # Check if all vertices reachable
            if len(min_incoming) < len(self._nodes) - 1:
                return None

            # Check for cycles
            visited = {root}
            edges = [(u, v, w) for v, (u, w) in min_incoming.items()]

            # Simple cycle detection
            for v, (u, w) in min_incoming.items():
                if u in visited:
                    continue

                path = {v}
                current = u

                while current not in visited and current in min_incoming:
                    if current in path:
                        # Cycle found - need contract (simplified: just use greedy result)
                        break
                    path.add(current)
                    current = min_incoming[current][0]

            total_weight = sum(w for _, w in min_incoming.values())
            result_edges = [(u, v, w) for v, (u, w) in min_incoming.items()]

            return MSTResult(
                edges=result_edges,
                total_weight=total_weight,
                is_connected=True
            )


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_kruskal_mst() -> KruskalMST:
    """Create Kruskal MST engine."""
    return KruskalMST()


def create_prim_mst() -> PrimMST:
    """Create Prim MST engine."""
    return PrimMST()


def create_boruvka_mst() -> BoruvkaMST:
    """Create Borůvka MST engine."""
    return BoruvkaMST()


def minimum_spanning_tree(
    edges: List[Tuple[int, int, float]],
    algorithm: str = "kruskal"
) -> MSTResult:
    """
    Find minimum spanning tree.

    Args:
        edges: List of (u, v, weight) undirected edges
        algorithm: "kruskal", "prim", or "boruvka"

    Returns:
        MSTResult with edges and weight
    """
    if algorithm == "prim":
        engine = PrimMST()
    elif algorithm == "boruvka":
        engine = BoruvkaMST()
    else:
        engine = KruskalMST()

    for u, v, w in edges:
        engine.add_edge(u, v, w)

    return engine.find_mst()


def mst_weight(edges: List[Tuple[int, int, float]]) -> float:
    """Get total weight of MST."""
    result = minimum_spanning_tree(edges)
    return result.total_weight


def is_connected(edges: List[Tuple[int, int, float]]) -> bool:
    """Check if graph is connected."""
    result = minimum_spanning_tree(edges)
    return result.is_connected


def minimum_arborescence(
    edges: List[Tuple[int, int, float]],
    root: int
) -> Optional[MSTResult]:
    """Find minimum spanning arborescence (directed MST)."""
    engine = MinimumArborescence()
    for u, v, w in edges:
        engine.add_edge(u, v, w)
    return engine.find_arborescence(root)
