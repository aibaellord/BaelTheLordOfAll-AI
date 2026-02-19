"""
BAEL Clique Algorithms Engine
=============================

Clique finding and related algorithms.

"Ba'el finds the most connected." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple, Set, FrozenSet
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum, auto

logger = logging.getLogger("BAEL.CliqueAlgorithms")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class CliqueResult:
    """Clique algorithm result."""
    clique: Set[int] = field(default_factory=set)
    size: int = 0
    all_cliques: List[Set[int]] = field(default_factory=list)
    count: int = 0
    nodes_explored: int = 0


@dataclass
class GraphStats:
    """Graph statistics for optimization."""
    vertices: int
    edges: int
    density: float
    max_degree: int
    avg_degree: float
    degeneracy: int


# ============================================================================
# BRON-KERBOSCH ALGORITHM
# ============================================================================

class BronKerbosch:
    """
    Bron-Kerbosch algorithm for finding cliques.

    Features:
    - Finds all maximal cliques
    - O(3^(n/3)) worst case
    - Pivoting for efficiency

    "Ba'el enumerates all cliques." — Ba'el
    """

    def __init__(self):
        """Initialize Bron-Kerbosch."""
        self._lock = threading.RLock()

    def find_all_maximal_cliques(
        self,
        n: int,
        edges: List[Tuple[int, int]]
    ) -> CliqueResult:
        """
        Find all maximal cliques.

        A maximal clique cannot be extended by adding more vertices.
        """
        with self._lock:
            # Build adjacency
            adj: Dict[int, Set[int]] = {i: set() for i in range(n)}
            for u, v in edges:
                adj[u].add(v)
                adj[v].add(u)

            all_cliques: List[Set[int]] = []
            nodes_explored = [0]

            def bron_kerbosch(R: Set[int], P: Set[int], X: Set[int]):
                nodes_explored[0] += 1

                if not P and not X:
                    # R is a maximal clique
                    all_cliques.append(set(R))
                    return

                # Choose pivot from P ∪ X with maximum neighbors in P
                pivot = max(P | X, key=lambda v: len(P & adj[v]), default=None)

                if pivot is None:
                    return

                # Iterate over P \ N(pivot)
                for v in list(P - adj[pivot]):
                    new_R = R | {v}
                    new_P = P & adj[v]
                    new_X = X & adj[v]

                    bron_kerbosch(new_R, new_P, new_X)

                    P.remove(v)
                    X.add(v)

            bron_kerbosch(set(), set(range(n)), set())

            max_clique = max(all_cliques, key=len) if all_cliques else set()

            return CliqueResult(
                clique=max_clique,
                size=len(max_clique),
                all_cliques=all_cliques,
                count=len(all_cliques),
                nodes_explored=nodes_explored[0]
            )

    def find_cliques_of_size(
        self,
        n: int,
        edges: List[Tuple[int, int]],
        k: int
    ) -> CliqueResult:
        """
        Find all cliques of exactly size k.
        """
        with self._lock:
            adj: Dict[int, Set[int]] = {i: set() for i in range(n)}
            for u, v in edges:
                adj[u].add(v)
                adj[v].add(u)

            k_cliques: List[Set[int]] = []
            nodes_explored = [0]

            def find_k_clique(R: Set[int], P: Set[int]):
                nodes_explored[0] += 1

                if len(R) == k:
                    k_cliques.append(set(R))
                    return

                if len(R) + len(P) < k:
                    return  # Can't reach size k

                for v in list(P):
                    new_R = R | {v}
                    new_P = {u for u in P if u > v and u in adj[v]}

                    find_k_clique(new_R, new_P)

            find_k_clique(set(), set(range(n)))

            return CliqueResult(
                clique=k_cliques[0] if k_cliques else set(),
                size=k,
                all_cliques=k_cliques,
                count=len(k_cliques),
                nodes_explored=nodes_explored[0]
            )


# ============================================================================
# MAXIMUM CLIQUE
# ============================================================================

class MaximumClique:
    """
    Maximum clique algorithms.

    Features:
    - Branch and bound with pruning
    - Greedy coloring for upper bound
    - Degree ordering

    "Ba'el finds the largest clique." — Ba'el
    """

    def __init__(self):
        """Initialize maximum clique finder."""
        self._lock = threading.RLock()

    def find(self, n: int, edges: List[Tuple[int, int]]) -> CliqueResult:
        """
        Find maximum clique.

        Uses branch and bound with coloring-based bounds.
        """
        with self._lock:
            if n == 0:
                return CliqueResult()

            # Build adjacency
            adj: Dict[int, Set[int]] = {i: set() for i in range(n)}
            for u, v in edges:
                adj[u].add(v)
                adj[v].add(u)

            # Order vertices by degree (descending)
            order = sorted(range(n), key=lambda v: len(adj[v]), reverse=True)

            max_clique = set()
            nodes_explored = [0]

            def greedy_coloring(vertices: List[int]) -> int:
                """Upper bound via greedy coloring."""
                if not vertices:
                    return 0

                colors = {}
                for v in vertices:
                    neighbor_colors = {colors[u] for u in adj[v] if u in colors}
                    for c in range(len(vertices)):
                        if c not in neighbor_colors:
                            colors[v] = c
                            break

                return max(colors.values()) + 1 if colors else 0

            def branch_and_bound(R: Set[int], P: List[int]):
                nonlocal max_clique
                nodes_explored[0] += 1

                if not P:
                    if len(R) > len(max_clique):
                        max_clique = set(R)
                    return

                # Upper bound
                if len(R) + len(P) <= len(max_clique):
                    return

                # Coloring bound
                color_bound = greedy_coloring(P)
                if len(R) + color_bound <= len(max_clique):
                    return

                for i, v in enumerate(P):
                    new_R = R | {v}
                    new_P = [u for u in P[i + 1:] if u in adj[v]]

                    branch_and_bound(new_R, new_P)

            branch_and_bound(set(), order)

            return CliqueResult(
                clique=max_clique,
                size=len(max_clique),
                nodes_explored=nodes_explored[0]
            )

    def greedy(self, n: int, edges: List[Tuple[int, int]]) -> CliqueResult:
        """
        Greedy approximation for maximum clique.

        Fast but not optimal.
        """
        with self._lock:
            if n == 0:
                return CliqueResult()

            adj: Dict[int, Set[int]] = {i: set() for i in range(n)}
            for u, v in edges:
                adj[u].add(v)
                adj[v].add(u)

            # Start with highest degree vertex
            clique = {max(range(n), key=lambda v: len(adj[v]))}

            # Greedily add vertices
            candidates = list(range(n))

            while candidates:
                # Find vertex connected to all in clique with max connections
                best_v = None
                best_score = -1

                for v in candidates:
                    if v in clique:
                        continue

                    if all(u in adj[v] for u in clique):
                        score = len(adj[v] & set(candidates))
                        if score > best_score:
                            best_score = score
                            best_v = v

                if best_v is None:
                    break

                clique.add(best_v)
                candidates = [v for v in candidates if v in adj[best_v] or v in clique]

            return CliqueResult(clique=clique, size=len(clique))


# ============================================================================
# K-CLIQUE DETECTION
# ============================================================================

class KCliqueDetector:
    """
    K-clique detection algorithms.

    "Ba'el detects k-cliques." — Ba'el
    """

    def __init__(self):
        """Initialize k-clique detector."""
        self._lock = threading.RLock()

    def has_k_clique(
        self,
        n: int,
        edges: List[Tuple[int, int]],
        k: int
    ) -> bool:
        """
        Check if graph contains a k-clique.

        Early termination when found.
        """
        with self._lock:
            if k <= 0:
                return True
            if k == 1:
                return n > 0
            if k == 2:
                return len(edges) > 0

            adj: Dict[int, Set[int]] = {i: set() for i in range(n)}
            for u, v in edges:
                adj[u].add(v)
                adj[v].add(u)

            # Prune vertices with degree < k-1
            active = {v for v in range(n) if len(adj[v]) >= k - 1}

            def has_clique(R: Set[int], P: Set[int]) -> bool:
                if len(R) == k:
                    return True

                if len(R) + len(P) < k:
                    return False

                for v in list(P):
                    new_R = R | {v}
                    new_P = {u for u in P if u > v and u in adj[v]}

                    if has_clique(new_R, new_P):
                        return True

                return False

            return has_clique(set(), active)

    def find_k_clique(
        self,
        n: int,
        edges: List[Tuple[int, int]],
        k: int
    ) -> Optional[Set[int]]:
        """
        Find one k-clique if exists.
        """
        with self._lock:
            result = BronKerbosch().find_cliques_of_size(n, edges, k)
            return result.clique if result.count > 0 else None


# ============================================================================
# CLIQUE COVER
# ============================================================================

class CliqueCover:
    """
    Clique cover algorithms.

    Find minimum number of cliques to cover all vertices.

    "Ba'el covers with cliques." — Ba'el
    """

    def __init__(self):
        """Initialize clique cover."""
        self._lock = threading.RLock()

    def greedy_cover(
        self,
        n: int,
        edges: List[Tuple[int, int]]
    ) -> Tuple[int, List[Set[int]]]:
        """
        Greedy approximation for clique cover.

        Repeatedly finds maximal cliques.
        """
        with self._lock:
            if n == 0:
                return 0, []

            adj: Dict[int, Set[int]] = {i: set() for i in range(n)}
            for u, v in edges:
                adj[u].add(v)
                adj[v].add(u)

            uncovered = set(range(n))
            cover: List[Set[int]] = []

            while uncovered:
                # Find maximal clique in uncovered
                clique = self._greedy_maximal_clique(uncovered, adj)
                cover.append(clique)
                uncovered -= clique

            return len(cover), cover

    def _greedy_maximal_clique(
        self,
        vertices: Set[int],
        adj: Dict[int, Set[int]]
    ) -> Set[int]:
        """Find maximal clique greedily."""
        if not vertices:
            return set()

        # Start with highest degree vertex in subgraph
        v = max(vertices, key=lambda x: len(adj[x] & vertices))
        clique = {v}
        candidates = list(adj[v] & vertices)

        for u in sorted(candidates, key=lambda x: len(adj[x]), reverse=True):
            if all(w in adj[u] for w in clique):
                clique.add(u)

        return clique


# ============================================================================
# CLIQUE PERCOLATION
# ============================================================================

class CliquePercolation:
    """
    Clique percolation method for community detection.

    Features:
    - Finds overlapping communities
    - Based on k-cliques sharing k-1 vertices

    "Ba'el percolates through cliques." — Ba'el
    """

    def __init__(self, k: int = 3):
        """Initialize clique percolation."""
        self._k = k
        self._lock = threading.RLock()

    def find_communities(
        self,
        n: int,
        edges: List[Tuple[int, int]]
    ) -> List[Set[int]]:
        """
        Find overlapping communities using k-clique percolation.
        """
        with self._lock:
            # Find all k-cliques
            bk = BronKerbosch()
            result = bk.find_cliques_of_size(n, edges, self._k)
            k_cliques = result.all_cliques

            if not k_cliques:
                return []

            # Build clique adjacency (share k-1 vertices)
            clique_list = [frozenset(c) for c in k_cliques]
            m = len(clique_list)

            clique_adj: Dict[int, Set[int]] = {i: set() for i in range(m)}

            for i in range(m):
                for j in range(i + 1, m):
                    if len(clique_list[i] & clique_list[j]) >= self._k - 1:
                        clique_adj[i].add(j)
                        clique_adj[j].add(i)

            # Find connected components of cliques
            visited = [False] * m
            communities: List[Set[int]] = []

            for start in range(m):
                if visited[start]:
                    continue

                community: Set[int] = set()
                stack = [start]

                while stack:
                    ci = stack.pop()
                    if visited[ci]:
                        continue

                    visited[ci] = True
                    community |= clique_list[ci]

                    for cj in clique_adj[ci]:
                        if not visited[cj]:
                            stack.append(cj)

                if community:
                    communities.append(community)

            return communities


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_bron_kerbosch() -> BronKerbosch:
    """Create Bron-Kerbosch algorithm."""
    return BronKerbosch()


def create_maximum_clique() -> MaximumClique:
    """Create maximum clique finder."""
    return MaximumClique()


def create_k_clique_detector() -> KCliqueDetector:
    """Create k-clique detector."""
    return KCliqueDetector()


def create_clique_cover() -> CliqueCover:
    """Create clique cover solver."""
    return CliqueCover()


def create_clique_percolation(k: int = 3) -> CliquePercolation:
    """Create clique percolation."""
    return CliquePercolation(k)


def find_maximum_clique(n: int, edges: List[Tuple[int, int]]) -> Set[int]:
    """Find maximum clique in graph."""
    return MaximumClique().find(n, edges).clique


def find_all_maximal_cliques(
    n: int,
    edges: List[Tuple[int, int]]
) -> List[Set[int]]:
    """Find all maximal cliques."""
    return BronKerbosch().find_all_maximal_cliques(n, edges).all_cliques


def has_clique_of_size(n: int, edges: List[Tuple[int, int]], k: int) -> bool:
    """Check if graph has k-clique."""
    return KCliqueDetector().has_k_clique(n, edges, k)


def clique_cover(n: int, edges: List[Tuple[int, int]]) -> List[Set[int]]:
    """Find greedy clique cover."""
    return CliqueCover().greedy_cover(n, edges)[1]


def clique_communities(
    n: int,
    edges: List[Tuple[int, int]],
    k: int = 3
) -> List[Set[int]]:
    """Find overlapping communities via clique percolation."""
    return CliquePercolation(k).find_communities(n, edges)
