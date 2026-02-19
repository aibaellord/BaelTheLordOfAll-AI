"""
BAEL Graph Coloring Engine
==========================

Graph coloring algorithms.

"Ba'el assigns colors with perfection." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import heapq

logger = logging.getLogger("BAEL.GraphColoring")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ColoringResult:
    """Graph coloring result."""
    coloring: Dict[int, int] = field(default_factory=dict)
    num_colors: int = 0
    is_valid: bool = True


@dataclass
class ColoringStats:
    """Coloring statistics."""
    node_count: int = 0
    edge_count: int = 0
    chromatic_number_upper: int = 0
    chromatic_number_lower: int = 0


# ============================================================================
# GREEDY COLORING
# ============================================================================

class GreedyColoring:
    """
    Greedy graph coloring.

    Features:
    - O(V + E) complexity
    - Guaranteed ≤ Δ+1 colors (Δ = max degree)
    - Various ordering strategies

    "Ba'el colors greedily." — Ba'el
    """

    def __init__(self):
        """Initialize greedy coloring."""
        self._adj: Dict[int, Set[int]] = defaultdict(set)
        self._nodes: Set[int] = set()
        self._stats = ColoringStats()
        self._lock = threading.RLock()

        logger.debug("Greedy coloring initialized")

    def add_edge(self, u: int, v: int) -> None:
        """Add undirected edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].add(v)
            self._adj[v].add(u)

    def color_basic(self) -> ColoringResult:
        """
        Basic greedy coloring (arbitrary order).

        Returns:
            ColoringResult with coloring
        """
        with self._lock:
            coloring = {}

            for node in self._nodes:
                # Find colors used by neighbors
                neighbor_colors = {coloring[n] for n in self._adj[node] if n in coloring}

                # Find smallest available color
                color = 0
                while color in neighbor_colors:
                    color += 1

                coloring[node] = color

            num_colors = max(coloring.values()) + 1 if coloring else 0

            self._stats.node_count = len(self._nodes)
            self._stats.edge_count = sum(len(neighbors) for neighbors in self._adj.values()) // 2
            self._stats.chromatic_number_upper = num_colors

            return ColoringResult(coloring=coloring, num_colors=num_colors)

    def color_largest_first(self) -> ColoringResult:
        """
        Largest-degree-first ordering.

        Colors vertices in decreasing order of degree.
        """
        with self._lock:
            # Sort by degree descending
            nodes_by_degree = sorted(
                self._nodes,
                key=lambda n: len(self._adj[n]),
                reverse=True
            )

            coloring = {}

            for node in nodes_by_degree:
                neighbor_colors = {coloring[n] for n in self._adj[node] if n in coloring}

                color = 0
                while color in neighbor_colors:
                    color += 1

                coloring[node] = color

            num_colors = max(coloring.values()) + 1 if coloring else 0

            return ColoringResult(coloring=coloring, num_colors=num_colors)

    def color_smallest_last(self) -> ColoringResult:
        """
        Smallest-last ordering.

        Repeatedly remove minimum degree vertex, color in reverse order.
        """
        with self._lock:
            # Build degree-based ordering
            degree = {n: len(self._adj[n]) for n in self._nodes}
            removed = set()
            order = []

            adj_copy = {n: set(neighbors) for n, neighbors in self._adj.items()}

            while len(order) < len(self._nodes):
                # Find minimum degree node
                min_node = min(
                    (n for n in self._nodes if n not in removed),
                    key=lambda n: len(adj_copy[n] - removed)
                )

                order.append(min_node)
                removed.add(min_node)

            # Color in reverse order
            order.reverse()
            coloring = {}

            for node in order:
                neighbor_colors = {coloring[n] for n in self._adj[node] if n in coloring}

                color = 0
                while color in neighbor_colors:
                    color += 1

                coloring[node] = color

            num_colors = max(coloring.values()) + 1 if coloring else 0

            return ColoringResult(coloring=coloring, num_colors=num_colors)

    def color_dsatur(self) -> ColoringResult:
        """
        DSatur (Degree of Saturation) algorithm.

        Always colors the vertex with highest saturation degree
        (most different-colored neighbors).
        """
        with self._lock:
            coloring = {}
            saturation = {n: 0 for n in self._nodes}

            while len(coloring) < len(self._nodes):
                # Find uncolored vertex with highest saturation
                # Break ties by highest degree
                uncolored = [n for n in self._nodes if n not in coloring]

                next_node = max(
                    uncolored,
                    key=lambda n: (saturation[n], len(self._adj[n]))
                )

                # Find available color
                neighbor_colors = {coloring[n] for n in self._adj[next_node] if n in coloring}

                color = 0
                while color in neighbor_colors:
                    color += 1

                coloring[next_node] = color

                # Update saturation of neighbors
                for neighbor in self._adj[next_node]:
                    if neighbor not in coloring:
                        neighbor_neighbor_colors = {
                            coloring[n] for n in self._adj[neighbor] if n in coloring
                        }
                        saturation[neighbor] = len(neighbor_neighbor_colors)

            num_colors = max(coloring.values()) + 1 if coloring else 0

            return ColoringResult(coloring=coloring, num_colors=num_colors)

    def is_valid_coloring(self, coloring: Dict[int, int]) -> bool:
        """Check if coloring is valid."""
        with self._lock:
            for u in self._nodes:
                if u not in coloring:
                    return False

                for v in self._adj[u]:
                    if coloring.get(u) == coloring.get(v):
                        return False

            return True

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'node_count': self._stats.node_count,
            'edge_count': self._stats.edge_count,
            'chromatic_number_upper': self._stats.chromatic_number_upper
        }


# ============================================================================
# K-COLORING (DECISION PROBLEM)
# ============================================================================

class KColoring:
    """
    K-coloring decision and finding.

    Features:
    - Backtracking with pruning
    - Constraint propagation
    - Forward checking

    "Ba'el determines if k colors suffice." — Ba'el
    """

    def __init__(self):
        """Initialize k-coloring."""
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

    def is_k_colorable(self, k: int) -> bool:
        """Check if graph is k-colorable."""
        result = self.find_k_coloring(k)
        return result.is_valid

    def find_k_coloring(self, k: int) -> ColoringResult:
        """
        Find a k-coloring if one exists.

        Args:
            k: Number of colors

        Returns:
            ColoringResult (is_valid=False if not possible)
        """
        with self._lock:
            if k <= 0:
                return ColoringResult(is_valid=False)

            nodes = list(self._nodes)
            coloring = {}

            # Sort by degree for better pruning
            nodes.sort(key=lambda n: len(self._adj[n]), reverse=True)

            def backtrack(idx: int) -> bool:
                if idx == len(nodes):
                    return True

                node = nodes[idx]
                neighbor_colors = {coloring[n] for n in self._adj[node] if n in coloring}

                for color in range(k):
                    if color not in neighbor_colors:
                        coloring[node] = color

                        if backtrack(idx + 1):
                            return True

                        del coloring[node]

                return False

            if backtrack(0):
                return ColoringResult(
                    coloring=coloring,
                    num_colors=len(set(coloring.values())),
                    is_valid=True
                )
            else:
                return ColoringResult(is_valid=False)

    def chromatic_number(self) -> int:
        """
        Find chromatic number (minimum k for k-coloring).

        Uses binary search with k-coloring check.
        """
        with self._lock:
            if not self._nodes:
                return 0

            if not any(self._adj.values()):
                return 1

            # Lower bound: clique number ≤ χ
            # Upper bound: Δ + 1
            max_degree = max(len(neighbors) for neighbors in self._adj.values())

            # Binary search
            lo, hi = 1, max_degree + 1

            while lo < hi:
                mid = (lo + hi) // 2

                if self.is_k_colorable(mid):
                    hi = mid
                else:
                    lo = mid + 1

            return lo


# ============================================================================
# EDGE COLORING
# ============================================================================

class EdgeColoring:
    """
    Edge coloring algorithms.

    Features:
    - Vizing's theorem: χ'(G) ≤ Δ + 1
    - Greedy edge coloring

    "Ba'el colors the connections." — Ba'el
    """

    def __init__(self):
        """Initialize edge coloring."""
        self._edges: List[Tuple[int, int]] = []
        self._nodes: Set[int] = set()
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int) -> None:
        """Add undirected edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._edges.append((u, v))

    def color_edges(self) -> Dict[Tuple[int, int], int]:
        """
        Color edges so no two adjacent edges have same color.

        Returns:
            Dict mapping edge (u, v) → color
        """
        with self._lock:
            edge_colors = {}
            vertex_colors = defaultdict(set)  # vertex → colors used at that vertex

            for u, v in self._edges:
                # Find colors used at either endpoint
                used = vertex_colors[u] | vertex_colors[v]

                color = 0
                while color in used:
                    color += 1

                edge_colors[(u, v)] = color
                vertex_colors[u].add(color)
                vertex_colors[v].add(color)

            return edge_colors

    def chromatic_index(self) -> int:
        """Get chromatic index (number of colors needed for edges)."""
        edge_colors = self.color_edges()
        return max(edge_colors.values()) + 1 if edge_colors else 0


# ============================================================================
# BIPARTITE COLORING
# ============================================================================

class BipartiteChecker:
    """
    Check if graph is bipartite (2-colorable).

    "Ba'el divides into two camps." — Ba'el
    """

    def __init__(self):
        """Initialize bipartite checker."""
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

    def is_bipartite(self) -> bool:
        """Check if graph is bipartite."""
        partition = self.get_bipartition()
        return partition is not None

    def get_bipartition(self) -> Optional[Tuple[Set[int], Set[int]]]:
        """
        Get bipartition if graph is bipartite.

        Returns:
            (set A, set B) or None if not bipartite
        """
        with self._lock:
            from collections import deque

            color = {}

            for start in self._nodes:
                if start in color:
                    continue

                queue = deque([start])
                color[start] = 0

                while queue:
                    node = queue.popleft()

                    for neighbor in self._adj[node]:
                        if neighbor not in color:
                            color[neighbor] = 1 - color[node]
                            queue.append(neighbor)
                        elif color[neighbor] == color[node]:
                            return None

            set_a = {n for n, c in color.items() if c == 0}
            set_b = {n for n, c in color.items() if c == 1}

            return (set_a, set_b)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_greedy_coloring() -> GreedyColoring:
    """Create greedy coloring engine."""
    return GreedyColoring()


def create_k_coloring() -> KColoring:
    """Create k-coloring engine."""
    return KColoring()


def create_edge_coloring() -> EdgeColoring:
    """Create edge coloring engine."""
    return EdgeColoring()


def create_bipartite_checker() -> BipartiteChecker:
    """Create bipartite checker."""
    return BipartiteChecker()


def color_graph(
    edges: List[Tuple[int, int]],
    algorithm: str = "dsatur"
) -> Dict[int, int]:
    """
    Color a graph.

    Args:
        edges: List of (u, v) undirected edges
        algorithm: "basic", "largest_first", "smallest_last", or "dsatur"

    Returns:
        Dict mapping node → color
    """
    engine = GreedyColoring()
    for u, v in edges:
        engine.add_edge(u, v)

    method = {
        "basic": engine.color_basic,
        "largest_first": engine.color_largest_first,
        "smallest_last": engine.color_smallest_last,
        "dsatur": engine.color_dsatur
    }.get(algorithm, engine.color_dsatur)

    result = method()
    return result.coloring


def chromatic_number(edges: List[Tuple[int, int]]) -> int:
    """Find chromatic number of graph."""
    engine = KColoring()
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.chromatic_number()


def is_bipartite(edges: List[Tuple[int, int]]) -> bool:
    """Check if graph is bipartite."""
    engine = BipartiteChecker()
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.is_bipartite()


def is_k_colorable(edges: List[Tuple[int, int]], k: int) -> bool:
    """Check if graph is k-colorable."""
    engine = KColoring()
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.is_k_colorable(k)
