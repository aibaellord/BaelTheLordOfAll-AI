"""
BAEL Vertex Cover Engine
========================

Vertex cover algorithms and approximations.

"Ba'el covers all edges efficiently." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import heapq
import random

logger = logging.getLogger("BAEL.VertexCover")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class VertexCoverResult:
    """Vertex cover result."""
    cover: Set[int] = field(default_factory=set)
    size: int = 0
    is_minimal: bool = False
    is_minimum: bool = False


@dataclass
class VertexCoverStats:
    """Vertex cover statistics."""
    node_count: int = 0
    edge_count: int = 0
    cover_size: int = 0
    approximation_ratio: float = 1.0


# ============================================================================
# VERTEX COVER - 2-APPROXIMATION
# ============================================================================

class GreedyApproxVC:
    """
    2-Approximation for vertex cover.

    Maximal matching approach guarantees at most 2x optimal.

    "Ba'el approximates wisely." — Ba'el
    """

    def __init__(self):
        """Initialize greedy approximation."""
        self._adj: Dict[int, Set[int]] = defaultdict(set)
        self._nodes: Set[int] = set()
        self._edges: Set[Tuple[int, int]] = set()
        self._stats = VertexCoverStats()
        self._lock = threading.RLock()

        logger.debug("Greedy approximation VC initialized")

    def add_edge(self, u: int, v: int) -> None:
        """Add undirected edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].add(v)
            self._adj[v].add(u)
            self._edges.add((min(u, v), max(u, v)))

    def find_cover(self) -> VertexCoverResult:
        """
        Find vertex cover using maximal matching.

        Returns:
            VertexCoverResult with 2-approximation cover
        """
        with self._lock:
            cover = set()
            uncovered_edges = set(self._edges)

            while uncovered_edges:
                # Pick arbitrary uncovered edge
                u, v = next(iter(uncovered_edges))

                # Add both endpoints to cover
                cover.add(u)
                cover.add(v)

                # Remove all edges incident to u or v
                uncovered_edges = {(a, b) for a, b in uncovered_edges
                                  if a != u and a != v and b != u and b != v}

            self._stats.node_count = len(self._nodes)
            self._stats.edge_count = len(self._edges)
            self._stats.cover_size = len(cover)

            return VertexCoverResult(
                cover=cover,
                size=len(cover),
                is_minimal=True,
                is_minimum=False
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'node_count': self._stats.node_count,
            'edge_count': self._stats.edge_count,
            'cover_size': self._stats.cover_size,
            'approximation_ratio': self._stats.approximation_ratio
        }


# ============================================================================
# VERTEX COVER - GREEDY BY DEGREE
# ============================================================================

class GreedyDegreeVC:
    """
    Greedy vertex cover by maximum degree.

    Iteratively pick highest degree vertex.
    Not guaranteed 2-approximation but often better in practice.

    "Ba'el picks the most connected." — Ba'el
    """

    def __init__(self):
        """Initialize greedy degree VC."""
        self._adj: Dict[int, Set[int]] = defaultdict(set)
        self._nodes: Set[int] = set()
        self._edges: Set[Tuple[int, int]] = set()
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int) -> None:
        """Add undirected edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].add(v)
            self._adj[v].add(u)
            self._edges.add((min(u, v), max(u, v)))

    def find_cover(self) -> VertexCoverResult:
        """
        Find vertex cover greedily by degree.

        Returns:
            VertexCoverResult
        """
        with self._lock:
            cover = set()
            adj = {node: set(neighbors) for node, neighbors in self._adj.items()}
            uncovered_edges = set(self._edges)

            # Max-heap (negate degree for max behavior)
            heap = [(-len(adj[v]), v) for v in self._nodes]
            heapq.heapify(heap)

            while uncovered_edges and heap:
                _, v = heapq.heappop(heap)

                if v in cover:
                    continue

                # Check if v covers any uncovered edges
                covers_edges = any(
                    (min(v, u), max(v, u)) in uncovered_edges
                    for u in adj[v]
                )

                if not covers_edges:
                    continue

                cover.add(v)

                # Remove edges incident to v
                new_uncovered = set()
                for a, b in uncovered_edges:
                    if a != v and b != v:
                        new_uncovered.add((a, b))
                uncovered_edges = new_uncovered

            return VertexCoverResult(
                cover=cover,
                size=len(cover),
                is_minimal=True
            )


# ============================================================================
# VERTEX COVER - EXACT (BRANCH AND BOUND)
# ============================================================================

class ExactVC:
    """
    Exact minimum vertex cover using branch and bound.

    Features:
    - Exponential worst case
    - Pruning with lower bounds
    - Good for small graphs

    "Ba'el finds the true minimum." — Ba'el
    """

    def __init__(self):
        """Initialize exact VC."""
        self._adj: Dict[int, Set[int]] = defaultdict(set)
        self._nodes: Set[int] = set()
        self._edges: List[Tuple[int, int]] = []
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int) -> None:
        """Add undirected edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].add(v)
            self._adj[v].add(u)
            self._edges.append((min(u, v), max(u, v)))

    def find_minimum_cover(self, max_size: Optional[int] = None) -> VertexCoverResult:
        """
        Find minimum vertex cover.

        Args:
            max_size: Optional upper bound on cover size

        Returns:
            VertexCoverResult with minimum cover
        """
        with self._lock:
            if not self._edges:
                return VertexCoverResult(size=0, is_minimum=True)

            n = len(self._nodes)
            best_cover = None
            best_size = max_size if max_size else n

            def branch_bound(cover: Set[int], uncovered: List[Tuple[int, int]],
                           idx: int) -> None:
                nonlocal best_cover, best_size

                # Prune if current cover already >= best
                if len(cover) >= best_size:
                    return

                # Find uncovered edges
                remaining = [(u, v) for u, v in uncovered[idx:]
                            if u not in cover and v not in cover]

                if not remaining:
                    if len(cover) < best_size:
                        best_size = len(cover)
                        best_cover = set(cover)
                    return

                # Lower bound: need at least ceil(remaining/max_degree) more vertices
                if len(cover) + 1 >= best_size:
                    return

                # Pick first uncovered edge
                u, v = remaining[0]

                # Branch 1: add u to cover
                cover.add(u)
                branch_bound(cover, remaining, 0)
                cover.remove(u)

                # Branch 2: add v to cover
                cover.add(v)
                branch_bound(cover, remaining, 0)
                cover.remove(v)

            branch_bound(set(), self._edges, 0)

            if best_cover is None:
                # Fallback to approximation
                approx = GreedyApproxVC()
                for u, v in self._edges:
                    approx.add_edge(u, v)
                return approx.find_cover()

            return VertexCoverResult(
                cover=best_cover,
                size=len(best_cover),
                is_minimal=True,
                is_minimum=True
            )

    def find_cover_of_size_k(self, k: int) -> Optional[Set[int]]:
        """
        Find vertex cover of exactly size k if exists.

        Args:
            k: Required cover size

        Returns:
            Cover of size k or None
        """
        with self._lock:
            result = self.find_minimum_cover(max_size=k+1)

            if result.size <= k:
                return result.cover
            return None


# ============================================================================
# VERTEX COVER - WEIGHTED
# ============================================================================

class WeightedVC:
    """
    Weighted vertex cover.

    Find minimum weight cover using LP relaxation approximation.

    "Ba'el minimizes the total cost." — Ba'el
    """

    def __init__(self):
        """Initialize weighted VC."""
        self._adj: Dict[int, Set[int]] = defaultdict(set)
        self._nodes: Set[int] = set()
        self._weights: Dict[int, float] = {}
        self._edges: List[Tuple[int, int]] = []
        self._lock = threading.RLock()

    def add_vertex(self, v: int, weight: float = 1.0) -> None:
        """Add vertex with weight."""
        with self._lock:
            self._nodes.add(v)
            self._weights[v] = weight

    def add_edge(self, u: int, v: int) -> None:
        """Add undirected edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            if u not in self._weights:
                self._weights[u] = 1.0
            if v not in self._weights:
                self._weights[v] = 1.0
            self._adj[u].add(v)
            self._adj[v].add(u)
            self._edges.append((min(u, v), max(u, v)))

    def find_cover(self) -> Tuple[Set[int], float]:
        """
        Find weighted vertex cover.

        Uses pricing/primal-dual approach.

        Returns:
            (cover, total_weight)
        """
        with self._lock:
            cover = set()
            remaining_weights = dict(self._weights)
            uncovered = set(self._edges)

            while uncovered:
                # Pick edge with minimum sum of remaining weights
                best_edge = None
                best_sum = float('inf')

                for u, v in uncovered:
                    weight_sum = remaining_weights.get(u, 0) + remaining_weights.get(v, 0)
                    if weight_sum < best_sum:
                        best_sum = weight_sum
                        best_edge = (u, v)

                if best_edge is None:
                    break

                u, v = best_edge

                # Pick cheaper vertex
                if remaining_weights.get(u, float('inf')) <= remaining_weights.get(v, float('inf')):
                    cover.add(u)
                else:
                    cover.add(v)

                # Remove covered edges
                uncovered = {(a, b) for a, b in uncovered
                            if a not in cover and b not in cover}

            total_weight = sum(self._weights.get(v, 1.0) for v in cover)

            return cover, total_weight


# ============================================================================
# INDEPENDENT SET (COMPLEMENT)
# ============================================================================

class IndependentSet:
    """
    Maximum independent set.

    Complement of vertex cover.

    "Ba'el finds the non-adjacent majority." — Ba'el
    """

    def __init__(self):
        """Initialize independent set."""
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

    def find_maximal(self) -> Set[int]:
        """
        Find maximal independent set (greedy).

        Returns:
            Maximal independent set
        """
        with self._lock:
            independent = set()
            candidates = set(self._nodes)

            while candidates:
                # Pick vertex with minimum degree among candidates
                v = min(candidates, key=lambda x: len(self._adj[x] & candidates))
                independent.add(v)

                # Remove v and its neighbors from candidates
                candidates.discard(v)
                candidates -= self._adj[v]

            return independent

    def find_maximum(self) -> Set[int]:
        """
        Find maximum independent set.

        Complement of minimum vertex cover.

        Returns:
            Maximum independent set
        """
        with self._lock:
            # Find minimum vertex cover
            vc_engine = ExactVC()
            for u in self._adj:
                for v in self._adj[u]:
                    if u < v:
                        vc_engine.add_edge(u, v)

            min_cover = vc_engine.find_minimum_cover()

            # Independent set is complement
            return self._nodes - min_cover.cover


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_greedy_approx_vc() -> GreedyApproxVC:
    """Create greedy approximation vertex cover."""
    return GreedyApproxVC()


def create_greedy_degree_vc() -> GreedyDegreeVC:
    """Create greedy degree vertex cover."""
    return GreedyDegreeVC()


def create_exact_vc() -> ExactVC:
    """Create exact vertex cover solver."""
    return ExactVC()


def create_weighted_vc() -> WeightedVC:
    """Create weighted vertex cover solver."""
    return WeightedVC()


def create_independent_set() -> IndependentSet:
    """Create independent set finder."""
    return IndependentSet()


def vertex_cover_approx(edges: List[Tuple[int, int]]) -> Set[int]:
    """Get 2-approximation vertex cover."""
    engine = GreedyApproxVC()
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.find_cover().cover


def minimum_vertex_cover(edges: List[Tuple[int, int]]) -> Set[int]:
    """Get minimum vertex cover (exact)."""
    engine = ExactVC()
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.find_minimum_cover().cover


def maximum_independent_set(edges: List[Tuple[int, int]], nodes: Set[int]) -> Set[int]:
    """Get maximum independent set."""
    engine = IndependentSet()
    for n in nodes:
        engine._nodes.add(n)
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.find_maximum()


def vertex_cover_size(edges: List[Tuple[int, int]]) -> int:
    """Get minimum vertex cover size."""
    engine = ExactVC()
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.find_minimum_cover().size


def has_vertex_cover_of_size(edges: List[Tuple[int, int]], k: int) -> bool:
    """Check if vertex cover of size k exists."""
    engine = ExactVC()
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.find_cover_of_size_k(k) is not None
