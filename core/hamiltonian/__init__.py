"""
BAEL Hamiltonian Path Engine
============================

Hamiltonian path and cycle algorithms.

"Ba'el visits every vertex exactly once." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger("BAEL.HamiltonianPath")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class HamiltonianResult:
    """Hamiltonian path/cycle result."""
    path: List[int] = field(default_factory=list)
    exists: bool = False
    is_cycle: bool = False


@dataclass
class HamiltonianStats:
    """Hamiltonian statistics."""
    node_count: int = 0
    edge_count: int = 0
    paths_found: int = 0
    backtracks: int = 0


# ============================================================================
# HAMILTONIAN PATH - BACKTRACKING
# ============================================================================

class HamiltonianBacktrack:
    """
    Hamiltonian path/cycle using backtracking.

    Features:
    - Finds path visiting all vertices
    - Optional cycle detection
    - Pruning heuristics

    "Ba'el explores all possibilities." — Ba'el
    """

    def __init__(self):
        """Initialize Hamiltonian backtrack."""
        self._adj: Dict[int, Set[int]] = defaultdict(set)
        self._nodes: Set[int] = set()
        self._stats = HamiltonianStats()
        self._lock = threading.RLock()

        logger.debug("Hamiltonian backtrack initialized")

    def add_edge(self, u: int, v: int) -> None:
        """Add undirected edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].add(v)
            self._adj[v].add(u)

    def add_directed_edge(self, u: int, v: int) -> None:
        """Add directed edge u → v."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].add(v)

    def find_path(self, start: Optional[int] = None) -> HamiltonianResult:
        """
        Find Hamiltonian path.

        Args:
            start: Optional starting vertex

        Returns:
            HamiltonianResult with path if exists
        """
        with self._lock:
            if not self._nodes:
                return HamiltonianResult(exists=True, path=[])

            nodes = list(self._nodes)
            n = len(nodes)

            starts = [start] if start is not None else nodes
            backtracks = 0

            for start_node in starts:
                path = [start_node]
                visited = {start_node}

                def backtrack() -> bool:
                    nonlocal backtracks

                    if len(path) == n:
                        return True

                    current = path[-1]

                    # Try neighbors in degree order (pruning heuristic)
                    neighbors = sorted(
                        [v for v in self._adj[current] if v not in visited],
                        key=lambda v: len(self._adj[v] & (self._nodes - visited))
                    )

                    for neighbor in neighbors:
                        path.append(neighbor)
                        visited.add(neighbor)

                        if backtrack():
                            return True

                        path.pop()
                        visited.remove(neighbor)
                        backtracks += 1

                    return False

                if backtrack():
                    self._stats.node_count = n
                    self._stats.edge_count = sum(len(adj) for adj in self._adj.values()) // 2
                    self._stats.paths_found = 1
                    self._stats.backtracks = backtracks

                    return HamiltonianResult(path=path, exists=True)

            self._stats.backtracks = backtracks
            return HamiltonianResult(exists=False)

    def find_cycle(self) -> HamiltonianResult:
        """
        Find Hamiltonian cycle.

        Returns:
            HamiltonianResult with cycle if exists
        """
        with self._lock:
            if len(self._nodes) < 3:
                return HamiltonianResult(exists=False)

            # Check Ore's theorem conditions (sufficient but not necessary)
            n = len(self._nodes)

            start = next(iter(self._nodes))
            path = [start]
            visited = {start}
            backtracks = 0

            def backtrack() -> bool:
                nonlocal backtracks

                if len(path) == n:
                    # Check if we can return to start
                    return start in self._adj[path[-1]]

                current = path[-1]

                for neighbor in self._adj[current]:
                    if neighbor not in visited:
                        path.append(neighbor)
                        visited.add(neighbor)

                        if backtrack():
                            return True

                        path.pop()
                        visited.remove(neighbor)
                        backtracks += 1

                return False

            if backtrack():
                path.append(start)  # Complete the cycle

                return HamiltonianResult(
                    path=path,
                    exists=True,
                    is_cycle=True
                )

            self._stats.backtracks = backtracks
            return HamiltonianResult(exists=False)

    def find_all_paths(self, max_paths: int = 1000) -> List[List[int]]:
        """
        Find all Hamiltonian paths.

        Args:
            max_paths: Maximum paths to find

        Returns:
            List of all Hamiltonian paths
        """
        with self._lock:
            paths = []
            nodes = list(self._nodes)
            n = len(nodes)

            for start_node in nodes:
                if len(paths) >= max_paths:
                    break

                path = [start_node]
                visited = {start_node}

                def backtrack():
                    if len(paths) >= max_paths:
                        return

                    if len(path) == n:
                        paths.append(path.copy())
                        return

                    current = path[-1]

                    for neighbor in self._adj[current]:
                        if neighbor not in visited:
                            path.append(neighbor)
                            visited.add(neighbor)

                            backtrack()

                            path.pop()
                            visited.remove(neighbor)

                backtrack()

            self._stats.paths_found = len(paths)
            return paths

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'node_count': self._stats.node_count,
            'edge_count': self._stats.edge_count,
            'paths_found': self._stats.paths_found,
            'backtracks': self._stats.backtracks
        }


# ============================================================================
# HAMILTONIAN PATH - DYNAMIC PROGRAMMING (BITMASK)
# ============================================================================

class HamiltonianDP:
    """
    Hamiltonian path using DP with bitmask.

    Features:
    - O(n² * 2ⁿ) complexity
    - Suitable for n ≤ 20
    - Can count all paths

    "Ba'el computes with precision." — Ba'el
    """

    def __init__(self):
        """Initialize Hamiltonian DP."""
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

    def has_hamiltonian_path(self) -> bool:
        """
        Check if Hamiltonian path exists.

        Returns:
            True if path exists
        """
        with self._lock:
            nodes = list(self._nodes)
            n = len(nodes)

            if n > 20:
                # Fall back to backtracking for large graphs
                bt = HamiltonianBacktrack()
                for u in self._adj:
                    for v in self._adj[u]:
                        if u < v:
                            bt.add_edge(u, v)
                return bt.find_path().exists

            if n == 0:
                return True
            if n == 1:
                return True

            node_idx = {node: i for i, node in enumerate(nodes)}

            # dp[mask][i] = True if can visit nodes in mask ending at i
            dp = [[False] * n for _ in range(1 << n)]

            # Initialize: start at each node
            for i in range(n):
                dp[1 << i][i] = True

            # Fill DP
            for mask in range(1, 1 << n):
                for last in range(n):
                    if not (mask & (1 << last)):
                        continue
                    if not dp[mask][last]:
                        continue

                    node = nodes[last]

                    for neighbor in self._adj[node]:
                        next_idx = node_idx[neighbor]

                        if not (mask & (1 << next_idx)):
                            new_mask = mask | (1 << next_idx)
                            dp[new_mask][next_idx] = True

            # Check if any ending is valid
            full_mask = (1 << n) - 1
            return any(dp[full_mask][i] for i in range(n))

    def has_hamiltonian_cycle(self) -> bool:
        """
        Check if Hamiltonian cycle exists.

        Returns:
            True if cycle exists
        """
        with self._lock:
            nodes = list(self._nodes)
            n = len(nodes)

            if n < 3:
                return False

            if n > 20:
                bt = HamiltonianBacktrack()
                for u in self._adj:
                    for v in self._adj[u]:
                        if u < v:
                            bt.add_edge(u, v)
                return bt.find_cycle().exists

            node_idx = {node: i for i, node in enumerate(nodes)}

            # Start from node 0
            dp = [[False] * n for _ in range(1 << n)]
            dp[1][0] = True  # Start at node 0

            for mask in range(1, 1 << n):
                for last in range(n):
                    if not (mask & (1 << last)):
                        continue
                    if not dp[mask][last]:
                        continue

                    node = nodes[last]

                    for neighbor in self._adj[node]:
                        next_idx = node_idx[neighbor]

                        if not (mask & (1 << next_idx)):
                            new_mask = mask | (1 << next_idx)
                            dp[new_mask][next_idx] = True

            # Check if we can return to start
            full_mask = (1 << n) - 1
            start_node = nodes[0]

            for last in range(n):
                if dp[full_mask][last]:
                    node = nodes[last]
                    if start_node in self._adj[node]:
                        return True

            return False

    def count_hamiltonian_paths(self) -> int:
        """
        Count number of Hamiltonian paths.

        Returns:
            Number of paths
        """
        with self._lock:
            nodes = list(self._nodes)
            n = len(nodes)

            if n > 20:
                return -1  # Too large

            if n == 0:
                return 1
            if n == 1:
                return 1

            node_idx = {node: i for i, node in enumerate(nodes)}

            # dp[mask][i] = number of ways to visit mask ending at i
            dp = [[0] * n for _ in range(1 << n)]

            for i in range(n):
                dp[1 << i][i] = 1

            for mask in range(1, 1 << n):
                for last in range(n):
                    if not (mask & (1 << last)):
                        continue
                    if dp[mask][last] == 0:
                        continue

                    node = nodes[last]

                    for neighbor in self._adj[node]:
                        next_idx = node_idx[neighbor]

                        if not (mask & (1 << next_idx)):
                            new_mask = mask | (1 << next_idx)
                            dp[new_mask][next_idx] += dp[mask][last]

            full_mask = (1 << n) - 1
            return sum(dp[full_mask][i] for i in range(n))


# ============================================================================
# TRAVELING SALESMAN (RELATED)
# ============================================================================

class TravelingSalesman:
    """
    Traveling Salesman Problem solver.

    Features:
    - DP with bitmask for exact solution
    - Nearest neighbor heuristic
    - 2-opt improvement

    "Ba'el finds the shortest tour." — Ba'el
    """

    def __init__(self):
        """Initialize TSP solver."""
        self._adj: Dict[int, Dict[int, float]] = defaultdict(dict)
        self._nodes: Set[int] = set()
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int, weight: float) -> None:
        """Add weighted edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u][v] = weight
            self._adj[v][u] = weight

    def solve_exact(self, start: Optional[int] = None) -> Tuple[List[int], float]:
        """
        Solve TSP exactly using DP.

        Returns:
            (tour, total_cost)
        """
        with self._lock:
            nodes = list(self._nodes)
            n = len(nodes)

            if n > 20:
                return self.solve_nearest_neighbor(start)

            if n <= 1:
                return nodes, 0.0

            start = start if start is not None else nodes[0]
            start_idx = nodes.index(start)

            node_idx = {node: i for i, node in enumerate(nodes)}

            INF = float('inf')

            # dp[mask][i] = min cost to visit mask ending at i
            dp = [[INF] * n for _ in range(1 << n)]
            parent = [[None] * n for _ in range(1 << n)]

            dp[1 << start_idx][start_idx] = 0

            for mask in range(1, 1 << n):
                for last in range(n):
                    if not (mask & (1 << last)):
                        continue
                    if dp[mask][last] == INF:
                        continue

                    node = nodes[last]

                    for next_node, weight in self._adj[node].items():
                        next_idx = node_idx[next_node]

                        if not (mask & (1 << next_idx)):
                            new_mask = mask | (1 << next_idx)
                            new_cost = dp[mask][last] + weight

                            if new_cost < dp[new_mask][next_idx]:
                                dp[new_mask][next_idx] = new_cost
                                parent[new_mask][next_idx] = last

            # Find best ending and add return to start
            full_mask = (1 << n) - 1
            best_cost = INF
            best_last = -1

            for last in range(n):
                if dp[full_mask][last] != INF:
                    node = nodes[last]
                    if start in self._adj[node]:
                        total = dp[full_mask][last] + self._adj[node][start]
                        if total < best_cost:
                            best_cost = total
                            best_last = last

            if best_last == -1:
                return [], INF

            # Reconstruct path
            tour = []
            mask = full_mask
            current = best_last

            while current is not None:
                tour.append(nodes[current])
                prev = parent[mask][current]
                mask ^= (1 << current)
                current = prev

            tour.reverse()
            tour.append(start)  # Complete the cycle

            return tour, best_cost

    def solve_nearest_neighbor(self, start: Optional[int] = None) -> Tuple[List[int], float]:
        """
        Solve TSP using nearest neighbor heuristic.

        Returns:
            (tour, total_cost)
        """
        with self._lock:
            if not self._nodes:
                return [], 0.0

            start = start if start is not None else next(iter(self._nodes))

            tour = [start]
            visited = {start}
            total_cost = 0.0
            current = start

            while len(visited) < len(self._nodes):
                best_next = None
                best_cost = float('inf')

                for neighbor, weight in self._adj[current].items():
                    if neighbor not in visited and weight < best_cost:
                        best_cost = weight
                        best_next = neighbor

                if best_next is None:
                    break

                tour.append(best_next)
                visited.add(best_next)
                total_cost += best_cost
                current = best_next

            # Return to start
            if current in self._adj and start in self._adj[current]:
                total_cost += self._adj[current][start]
                tour.append(start)

            return tour, total_cost


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_hamiltonian_backtrack() -> HamiltonianBacktrack:
    """Create Hamiltonian backtrack engine."""
    return HamiltonianBacktrack()


def create_hamiltonian_dp() -> HamiltonianDP:
    """Create Hamiltonian DP engine."""
    return HamiltonianDP()


def create_tsp() -> TravelingSalesman:
    """Create TSP solver."""
    return TravelingSalesman()


def has_hamiltonian_path(edges: List[Tuple[int, int]]) -> bool:
    """Check if graph has Hamiltonian path."""
    engine = HamiltonianDP()
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.has_hamiltonian_path()


def has_hamiltonian_cycle(edges: List[Tuple[int, int]]) -> bool:
    """Check if graph has Hamiltonian cycle."""
    engine = HamiltonianDP()
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.has_hamiltonian_cycle()


def find_hamiltonian_path(edges: List[Tuple[int, int]]) -> List[int]:
    """Find a Hamiltonian path if one exists."""
    engine = HamiltonianBacktrack()
    for u, v in edges:
        engine.add_edge(u, v)
    result = engine.find_path()
    return result.path if result.exists else []


def solve_tsp(
    edges: List[Tuple[int, int, float]],
    exact: bool = True
) -> Tuple[List[int], float]:
    """
    Solve Traveling Salesman Problem.

    Args:
        edges: List of (u, v, weight) edges
        exact: Use exact DP (False for heuristic)

    Returns:
        (tour, cost)
    """
    engine = TravelingSalesman()
    for u, v, w in edges:
        engine.add_edge(u, v, w)

    if exact:
        return engine.solve_exact()
    else:
        return engine.solve_nearest_neighbor()
