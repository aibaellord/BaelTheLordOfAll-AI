"""
BAEL Maximum Independent Set Engine
====================================

Find maximum independent sets in graphs.

"Ba'el selects the maximum without conflict." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import random

logger = logging.getLogger("BAEL.MaxIndependentSet")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class MISStats:
    """Maximum independent set statistics."""
    node_count: int = 0
    edge_count: int = 0
    mis_size: int = 0
    iterations: int = 0


# ============================================================================
# MAXIMUM INDEPENDENT SET ENGINE
# ============================================================================

class MaxIndependentSetEngine:
    """
    Maximum Independent Set (MIS) algorithms.

    Features:
    - Exact solution for small graphs (backtracking)
    - Greedy approximation for large graphs
    - Special algorithms for trees and bipartite graphs

    "Ba'el finds the largest conflict-free set." — Ba'el
    """

    def __init__(self):
        """Initialize MIS engine."""
        self._adj: Dict[int, Set[int]] = defaultdict(set)
        self._nodes: Set[int] = set()
        self._edges: Set[Tuple[int, int]] = set()
        self._stats = MISStats()
        self._lock = threading.RLock()

        logger.debug("Maximum independent set engine initialized")

    def add_node(self, node: int) -> None:
        """Add isolated node."""
        with self._lock:
            self._nodes.add(node)

    def add_edge(self, u: int, v: int) -> None:
        """Add undirected edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)

            edge = (min(u, v), max(u, v))
            if edge not in self._edges:
                self._edges.add(edge)
                self._adj[u].add(v)
                self._adj[v].add(u)

    def _is_independent(self, nodes: Set[int]) -> bool:
        """Check if node set is independent."""
        for node in nodes:
            for neighbor in self._adj[node]:
                if neighbor in nodes:
                    return False
        return True

    def solve_exact(self, max_iterations: int = 1000000) -> Set[int]:
        """
        Find exact MIS using backtracking with pruning.

        Warning: Exponential time for general graphs.

        Args:
            max_iterations: Max iterations before giving up

        Returns:
            Maximum independent set
        """
        with self._lock:
            self._stats.node_count = len(self._nodes)
            self._stats.edge_count = len(self._edges)
            self._stats.iterations = 0

            if not self._nodes:
                return set()

            best_mis: Set[int] = set()
            nodes = list(self._nodes)
            n = len(nodes)

            # Sort by degree (process low-degree nodes first)
            nodes.sort(key=lambda x: len(self._adj[x]))

            def backtrack(index: int, current: Set[int], excluded: Set[int]) -> bool:
                nonlocal best_mis

                self._stats.iterations += 1

                if self._stats.iterations > max_iterations:
                    return True  # Stop early

                # Pruning: even if we take all remaining, can't beat best
                remaining = n - index
                if len(current) + remaining <= len(best_mis):
                    return False

                if index == n:
                    if len(current) > len(best_mis):
                        best_mis = current.copy()
                    return False

                node = nodes[index]

                if node in excluded:
                    return backtrack(index + 1, current, excluded)

                # Branch 1: Include node
                new_excluded = excluded | self._adj[node]
                current.add(node)

                if backtrack(index + 1, current, new_excluded):
                    return True

                current.remove(node)

                # Branch 2: Exclude node
                if backtrack(index + 1, current, excluded):
                    return True

                return False

            backtrack(0, set(), set())

            self._stats.mis_size = len(best_mis)
            logger.info(f"Exact MIS: {len(best_mis)} nodes, "
                       f"{self._stats.iterations} iterations")

            return best_mis

    def solve_greedy(self) -> Set[int]:
        """
        Greedy approximation for MIS.

        Strategy: Always pick minimum degree node.

        Returns:
            Independent set (not necessarily maximum)
        """
        with self._lock:
            self._stats.node_count = len(self._nodes)
            self._stats.edge_count = len(self._edges)

            if not self._nodes:
                return set()

            # Working copy of degrees
            degree = {node: len(self._adj[node]) for node in self._nodes}
            available = set(self._nodes)
            mis = set()

            while available:
                # Pick minimum degree node
                min_node = min(available, key=lambda x: degree.get(x, 0))

                mis.add(min_node)
                available.remove(min_node)

                # Remove neighbors
                for neighbor in self._adj[min_node]:
                    if neighbor in available:
                        available.remove(neighbor)

            self._stats.mis_size = len(mis)
            logger.info(f"Greedy MIS: {len(mis)} nodes")

            return mis

    def solve_tree(self, root: Optional[int] = None) -> Set[int]:
        """
        Optimal MIS for trees using dynamic programming.

        O(n) time.

        Args:
            root: Root node (auto-detected if None)

        Returns:
            Maximum independent set
        """
        with self._lock:
            if not self._nodes:
                return set()

            if root is None:
                root = next(iter(self._nodes))

            # DP: dp[node][0] = MIS size if node NOT included
            #     dp[node][1] = MIS size if node included
            dp = {node: [0, 1] for node in self._nodes}
            include = {node: [set(), {node}] for node in self._nodes}

            visited = set()

            def dfs(node: int, parent: int = -1) -> None:
                visited.add(node)

                for child in self._adj[node]:
                    if child not in visited:
                        dfs(child, node)

                        # If node not included, child can be either
                        if dp[child][0] > dp[child][1]:
                            dp[node][0] += dp[child][0]
                            include[node][0] |= include[child][0]
                        else:
                            dp[node][0] += dp[child][1]
                            include[node][0] |= include[child][1]

                        # If node included, child must not be
                        dp[node][1] += dp[child][0]
                        include[node][1] |= include[child][0]

            dfs(root)

            if dp[root][0] > dp[root][1]:
                mis = include[root][0]
            else:
                mis = include[root][1]

            self._stats.mis_size = len(mis)
            logger.info(f"Tree MIS: {len(mis)} nodes")

            return mis

    def solve_randomized(self, iterations: int = 1000) -> Set[int]:
        """
        Randomized local search for MIS.

        Args:
            iterations: Number of random restarts

        Returns:
            Best independent set found
        """
        with self._lock:
            if not self._nodes:
                return set()

            best_mis = set()
            nodes = list(self._nodes)

            for _ in range(iterations):
                # Random order
                random.shuffle(nodes)

                mis = set()
                excluded = set()

                for node in nodes:
                    if node not in excluded:
                        mis.add(node)
                        excluded |= self._adj[node]

                if len(mis) > len(best_mis):
                    best_mis = mis

            self._stats.mis_size = len(best_mis)
            self._stats.iterations = iterations

            return best_mis

    def is_maximal(self, mis: Set[int]) -> bool:
        """Check if MIS is maximal (no node can be added)."""
        if not self._is_independent(mis):
            return False

        for node in self._nodes:
            if node not in mis:
                # Check if node can be added
                can_add = all(neighbor not in mis for neighbor in self._adj[node])
                if can_add:
                    return False

        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'node_count': self._stats.node_count,
            'edge_count': self._stats.edge_count,
            'mis_size': self._stats.mis_size,
            'iterations': self._stats.iterations
        }


# ============================================================================
# MAXIMUM CLIQUE (COMPLEMENT OF MIS)
# ============================================================================

class MaxCliqueEngine:
    """
    Maximum Clique using MIS on complement graph.

    "Ba'el finds the largest complete subgraph." — Ba'el
    """

    def __init__(self):
        """Initialize max clique engine."""
        self._nodes: Set[int] = set()
        self._edges: Set[Tuple[int, int]] = set()
        self._lock = threading.RLock()

    def add_node(self, node: int) -> None:
        """Add node."""
        with self._lock:
            self._nodes.add(node)

    def add_edge(self, u: int, v: int) -> None:
        """Add edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._edges.add((min(u, v), max(u, v)))

    def solve(self) -> Set[int]:
        """Find maximum clique."""
        with self._lock:
            if len(self._nodes) <= 1:
                return self._nodes.copy()

            # Build complement graph
            mis_engine = MaxIndependentSetEngine()

            for node in self._nodes:
                mis_engine.add_node(node)

            nodes = list(self._nodes)
            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    u, v = nodes[i], nodes[j]
                    edge = (min(u, v), max(u, v))

                    if edge not in self._edges:
                        # Edge NOT in original = edge in complement
                        mis_engine.add_edge(u, v)

            # MIS in complement = max clique in original
            return mis_engine.solve_exact()


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_mis_engine() -> MaxIndependentSetEngine:
    """Create MIS engine."""
    return MaxIndependentSetEngine()


def create_max_clique_engine() -> MaxCliqueEngine:
    """Create max clique engine."""
    return MaxCliqueEngine()


def find_maximum_independent_set(
    edges: List[Tuple[int, int]],
    method: str = "greedy"
) -> Set[int]:
    """
    Find maximum independent set.

    Args:
        edges: List of (u, v) edges
        method: "exact", "greedy", or "randomized"

    Returns:
        Maximum independent set
    """
    engine = MaxIndependentSetEngine()

    for u, v in edges:
        engine.add_edge(u, v)

    if method == "exact":
        return engine.solve_exact()
    elif method == "randomized":
        return engine.solve_randomized()
    else:
        return engine.solve_greedy()


def find_maximum_clique(edges: List[Tuple[int, int]]) -> Set[int]:
    """Find maximum clique in graph."""
    engine = MaxCliqueEngine()

    for u, v in edges:
        engine.add_edge(u, v)

    return engine.solve()
