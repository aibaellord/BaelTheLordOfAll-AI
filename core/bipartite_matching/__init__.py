"""
BAEL Maximum Bipartite Matching Engine
======================================

Maximum matching in bipartite graphs.

"Ba'el pairs perfectly." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque

logger = logging.getLogger("BAEL.BipartiteMatching")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class MatchingStats:
    """Matching statistics."""
    left_count: int = 0
    right_count: int = 0
    edge_count: int = 0
    matching_size: int = 0


# ============================================================================
# HUNGARIAN ALGORITHM (KUHN'S / HOPCROFT-KARP)
# ============================================================================

class HungarianMatching:
    """
    Maximum bipartite matching using Kuhn's algorithm.

    Features:
    - O(V * E) complexity
    - Augmenting path approach
    - Perfect matching detection

    "Ba'el finds the perfect pairing." — Ba'el
    """

    def __init__(self):
        """Initialize Hungarian matching."""
        self._left: Set[int] = set()
        self._right: Set[int] = set()
        self._adj: Dict[int, List[int]] = defaultdict(list)

        self._match_left: Dict[int, int] = {}
        self._match_right: Dict[int, int] = {}
        self._stats = MatchingStats()
        self._built = False
        self._lock = threading.RLock()

        logger.debug("Hungarian matching initialized")

    def add_edge(self, left: int, right: int) -> None:
        """Add edge from left node to right node."""
        with self._lock:
            self._built = False
            self._left.add(left)
            self._right.add(right)
            self._adj[left].append(right)

    def solve(self) -> int:
        """
        Find maximum matching.

        Returns:
            Size of maximum matching
        """
        with self._lock:
            if self._built:
                return self._stats.matching_size

            self._stats.left_count = len(self._left)
            self._stats.right_count = len(self._right)
            self._stats.edge_count = sum(len(edges) for edges in self._adj.values())

            self._match_left.clear()
            self._match_right.clear()

            def try_kuhn(v: int, visited: Set[int]) -> bool:
                """Try to find augmenting path from v."""
                for to in self._adj[v]:
                    if to in visited:
                        continue

                    visited.add(to)

                    if to not in self._match_right or \
                       try_kuhn(self._match_right[to], visited):
                        self._match_left[v] = to
                        self._match_right[to] = v
                        return True

                return False

            matching = 0

            for v in self._left:
                visited = set()
                if try_kuhn(v, visited):
                    matching += 1

            self._stats.matching_size = matching
            self._built = True

            logger.info(f"Hungarian matching: {matching} pairs")
            return matching

    def get_matching(self) -> List[Tuple[int, int]]:
        """Get the matching as list of (left, right) pairs."""
        self.solve()
        return [(left, right) for left, right in self._match_left.items()]

    def get_left_match(self, left: int) -> Optional[int]:
        """Get match for left node."""
        self.solve()
        return self._match_left.get(left)

    def get_right_match(self, right: int) -> Optional[int]:
        """Get match for right node."""
        self.solve()
        return self._match_right.get(right)

    def is_perfect_matching(self) -> bool:
        """Check if matching is perfect (covers all smaller side)."""
        self.solve()
        min_side = min(len(self._left), len(self._right))
        return self._stats.matching_size == min_side

    def get_unmatched_left(self) -> Set[int]:
        """Get unmatched left nodes."""
        self.solve()
        return self._left - set(self._match_left.keys())

    def get_unmatched_right(self) -> Set[int]:
        """Get unmatched right nodes."""
        self.solve()
        return self._right - set(self._match_right.keys())

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        self.solve()
        return {
            'left_count': self._stats.left_count,
            'right_count': self._stats.right_count,
            'edge_count': self._stats.edge_count,
            'matching_size': self._stats.matching_size
        }


# ============================================================================
# HOPCROFT-KARP ALGORITHM
# ============================================================================

class HopcroftKarp:
    """
    Hopcroft-Karp algorithm for maximum bipartite matching.

    Features:
    - O(E * sqrt(V)) complexity
    - Faster for large graphs
    - Uses BFS + DFS phases

    "Ba'el matches at optimal speed." — Ba'el
    """

    def __init__(self):
        """Initialize Hopcroft-Karp."""
        self._left: Set[int] = set()
        self._right: Set[int] = set()
        self._adj: Dict[int, List[int]] = defaultdict(list)

        self._match_left: Dict[int, Optional[int]] = {}
        self._match_right: Dict[int, Optional[int]] = {}
        self._dist: Dict[int, int] = {}

        self._stats = MatchingStats()
        self._built = False
        self._lock = threading.RLock()

        # NIL node for unmatched
        self._NIL = None

    def add_edge(self, left: int, right: int) -> None:
        """Add edge from left to right."""
        with self._lock:
            self._built = False
            self._left.add(left)
            self._right.add(right)
            self._adj[left].append(right)

    def _bfs(self) -> bool:
        """BFS to find shortest augmenting paths."""
        queue = deque()

        for u in self._left:
            if self._match_left.get(u) is self._NIL:
                self._dist[u] = 0
                queue.append(u)
            else:
                self._dist[u] = float('inf')

        self._dist[self._NIL] = float('inf')

        while queue:
            u = queue.popleft()

            if self._dist[u] < self._dist[self._NIL]:
                for v in self._adj[u]:
                    paired = self._match_right.get(v, self._NIL)

                    if self._dist.get(paired, float('inf')) == float('inf'):
                        self._dist[paired] = self._dist[u] + 1

                        if paired is not self._NIL:
                            queue.append(paired)

        return self._dist[self._NIL] != float('inf')

    def _dfs(self, u: int) -> bool:
        """DFS to find augmenting path."""
        if u is self._NIL:
            return True

        for v in self._adj[u]:
            paired = self._match_right.get(v, self._NIL)

            if self._dist.get(paired, float('inf')) == self._dist[u] + 1:
                if self._dfs(paired):
                    self._match_right[v] = u
                    self._match_left[u] = v
                    return True

        self._dist[u] = float('inf')
        return False

    def solve(self) -> int:
        """
        Find maximum matching.

        Returns:
            Size of maximum matching
        """
        with self._lock:
            if self._built:
                return self._stats.matching_size

            self._stats.left_count = len(self._left)
            self._stats.right_count = len(self._right)
            self._stats.edge_count = sum(len(edges) for edges in self._adj.values())

            # Initialize all as unmatched
            for u in self._left:
                self._match_left[u] = self._NIL
            for v in self._right:
                self._match_right[v] = self._NIL

            matching = 0

            while self._bfs():
                for u in self._left:
                    if self._match_left[u] is self._NIL:
                        if self._dfs(u):
                            matching += 1

            self._stats.matching_size = matching
            self._built = True

            logger.info(f"Hopcroft-Karp matching: {matching} pairs")
            return matching

    def get_matching(self) -> List[Tuple[int, int]]:
        """Get the matching as list of (left, right) pairs."""
        self.solve()
        return [(u, v) for u, v in self._match_left.items() if v is not self._NIL]

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        self.solve()
        return {
            'left_count': self._stats.left_count,
            'right_count': self._stats.right_count,
            'edge_count': self._stats.edge_count,
            'matching_size': self._stats.matching_size
        }


# ============================================================================
# MINIMUM VERTEX COVER (KONIG'S THEOREM)
# ============================================================================

class MinimumVertexCover:
    """
    Minimum vertex cover for bipartite graphs.

    By König's theorem: |MVC| = |max matching|

    "Ba'el covers all edges minimally." — Ba'el
    """

    def __init__(self):
        """Initialize minimum vertex cover."""
        self._matching = HungarianMatching()
        self._left: Set[int] = set()
        self._right: Set[int] = set()
        self._adj: Dict[int, List[int]] = defaultdict(list)
        self._lock = threading.RLock()

    def add_edge(self, left: int, right: int) -> None:
        """Add edge."""
        with self._lock:
            self._left.add(left)
            self._right.add(right)
            self._adj[left].append(right)
            self._matching.add_edge(left, right)

    def solve(self) -> Tuple[Set[int], Set[int]]:
        """
        Find minimum vertex cover.

        Returns:
            (left_cover, right_cover) sets
        """
        with self._lock:
            self._matching.solve()

            match_left = self._matching._match_left
            match_right = self._matching._match_right

            # Start with unmatched left vertices
            unmatched_left = self._matching.get_unmatched_left()

            # Alternating BFS from unmatched left
            z_left = set()
            z_right = set()

            queue = deque(unmatched_left)
            z_left = set(unmatched_left)

            while queue:
                u = queue.popleft()

                if u in self._left:
                    # Explore unmatched edges
                    for v in self._adj[u]:
                        if v not in z_right:
                            z_right.add(v)
                            queue.append(v)
                else:
                    # u is in right, explore matching edge
                    if u in match_right:
                        v = match_right[u]
                        if v not in z_left:
                            z_left.add(v)
                            queue.append(v)

            # König's theorem: MVC = (L - Z_L) ∪ (R ∩ Z_R)
            left_cover = self._left - z_left
            right_cover = self._right & z_right

            return left_cover, right_cover

    def get_cover(self) -> Set[Tuple[str, int]]:
        """Get cover as set of ('left', id) or ('right', id)."""
        left_cover, right_cover = self.solve()
        result = {('left', v) for v in left_cover}
        result |= {('right', v) for v in right_cover}
        return result


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_hungarian_matching() -> HungarianMatching:
    """Create Hungarian matching engine."""
    return HungarianMatching()


def create_hopcroft_karp() -> HopcroftKarp:
    """Create Hopcroft-Karp matching engine."""
    return HopcroftKarp()


def create_vertex_cover() -> MinimumVertexCover:
    """Create minimum vertex cover engine."""
    return MinimumVertexCover()


def maximum_bipartite_matching(
    edges: List[Tuple[int, int]],
    algorithm: str = "hopcroft"
) -> List[Tuple[int, int]]:
    """
    Find maximum bipartite matching.

    Args:
        edges: List of (left, right) edges
        algorithm: "hungarian" or "hopcroft"

    Returns:
        List of matched pairs
    """
    if algorithm == "hungarian":
        engine = HungarianMatching()
    else:
        engine = HopcroftKarp()

    for left, right in edges:
        engine.add_edge(left, right)

    return engine.get_matching()


def matching_size(edges: List[Tuple[int, int]]) -> int:
    """Get size of maximum matching."""
    engine = HopcroftKarp()
    for left, right in edges:
        engine.add_edge(left, right)
    return engine.solve()


def minimum_vertex_cover(
    edges: List[Tuple[int, int]]
) -> Tuple[Set[int], Set[int]]:
    """Find minimum vertex cover."""
    engine = MinimumVertexCover()
    for left, right in edges:
        engine.add_edge(left, right)
    return engine.solve()


def is_perfect_matching_possible(
    left_count: int,
    right_count: int,
    edges: List[Tuple[int, int]]
) -> bool:
    """Check if perfect matching exists."""
    engine = HopcroftKarp()
    for left, right in edges:
        engine.add_edge(left, right)

    matching = engine.solve()
    return matching == min(left_count, right_count)
