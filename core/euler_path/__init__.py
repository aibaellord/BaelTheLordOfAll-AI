"""
BAEL Euler Path/Circuit Engine
==============================

Eulerian path and circuit discovery.

"Ba'el traverses every edge exactly once." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque

logger = logging.getLogger("BAEL.EulerPath")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class EulerStats:
    """Euler path statistics."""
    node_count: int = 0
    edge_count: int = 0
    is_eulerian: bool = False
    is_semi_eulerian: bool = False
    odd_degree_count: int = 0


# ============================================================================
# UNDIRECTED EULER PATH
# ============================================================================

class UndirectedEuler:
    """
    Eulerian path/circuit for undirected graphs.

    Features:
    - Hierholzer's algorithm O(E)
    - Path and circuit detection
    - Handles multigraphs

    "Ba'el walks every bridge once." — Ba'el
    """

    def __init__(self):
        """Initialize undirected Euler."""
        self._adj: Dict[int, List[int]] = defaultdict(list)
        self._edge_count: Dict[Tuple[int, int], int] = defaultdict(int)
        self._nodes: Set[int] = set()
        self._total_edges = 0
        self._lock = threading.RLock()

        logger.debug("Undirected Euler initialized")

    def add_edge(self, u: int, v: int) -> None:
        """Add undirected edge u--v."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)

            self._adj[u].append(v)
            self._adj[v].append(u)

            edge = (min(u, v), max(u, v))
            self._edge_count[edge] += 1
            self._total_edges += 1

    def get_degree(self, node: int) -> int:
        """Get degree of node."""
        with self._lock:
            return len(self._adj.get(node, []))

    def _is_connected(self) -> bool:
        """Check if graph is connected (ignoring isolated vertices)."""
        nodes_with_edges = {n for n in self._nodes if self._adj[n]}

        if not nodes_with_edges:
            return True

        start = next(iter(nodes_with_edges))
        visited = set()
        stack = [start]

        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)

            for neighbor in self._adj[node]:
                if neighbor not in visited:
                    stack.append(neighbor)

        return visited >= nodes_with_edges

    def has_euler_circuit(self) -> bool:
        """Check if Euler circuit exists (all vertices even degree)."""
        with self._lock:
            if not self._is_connected():
                return False

            for node in self._nodes:
                if len(self._adj[node]) % 2 != 0:
                    return False

            return True

    def has_euler_path(self) -> bool:
        """Check if Euler path exists (0 or 2 odd degree vertices)."""
        with self._lock:
            if not self._is_connected():
                return False

            odd_count = sum(1 for node in self._nodes if len(self._adj[node]) % 2 != 0)
            return odd_count == 0 or odd_count == 2

    def find_euler_circuit(self) -> Optional[List[int]]:
        """
        Find Euler circuit using Hierholzer's algorithm.

        Returns:
            List of vertices or None if no circuit exists
        """
        with self._lock:
            if not self.has_euler_circuit():
                return None

            if self._total_edges == 0:
                if self._nodes:
                    return [next(iter(self._nodes))]
                return []

            # Copy adjacency for modification
            adj = {node: list(neighbors) for node, neighbors in self._adj.items()}

            # Start from any vertex with edges
            start = next(n for n in self._nodes if adj[n])
            stack = [start]
            circuit = []

            while stack:
                v = stack[-1]

                if adj[v]:
                    u = adj[v].pop()
                    # Remove reverse edge
                    adj[u].remove(v)
                    stack.append(u)
                else:
                    circuit.append(stack.pop())

            return circuit[::-1]

    def find_euler_path(self) -> Optional[List[int]]:
        """
        Find Euler path.

        Returns:
            List of vertices or None if no path exists
        """
        with self._lock:
            if not self.has_euler_path():
                return None

            if self._total_edges == 0:
                if self._nodes:
                    return [next(iter(self._nodes))]
                return []

            # Find odd degree vertices
            odd_vertices = [n for n in self._nodes if len(self._adj[n]) % 2 != 0]

            if len(odd_vertices) == 0:
                # Euler circuit is also a path
                return self.find_euler_circuit()

            # Start from an odd degree vertex
            adj = {node: list(neighbors) for node, neighbors in self._adj.items()}

            start = odd_vertices[0]
            stack = [start]
            path = []

            while stack:
                v = stack[-1]

                if adj[v]:
                    u = adj[v].pop()
                    adj[u].remove(v)
                    stack.append(u)
                else:
                    path.append(stack.pop())

            return path[::-1]

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        odd_count = sum(1 for node in self._nodes if len(self._adj[node]) % 2 != 0)

        return {
            'node_count': len(self._nodes),
            'edge_count': self._total_edges,
            'is_eulerian': self.has_euler_circuit(),
            'is_semi_eulerian': self.has_euler_path() and not self.has_euler_circuit(),
            'odd_degree_count': odd_count
        }


# ============================================================================
# DIRECTED EULER PATH
# ============================================================================

class DirectedEuler:
    """
    Eulerian path/circuit for directed graphs.

    Features:
    - Hierholzer's algorithm O(E)
    - In-degree/out-degree tracking
    - Handles multigraphs

    "Ba'el follows every arrow once." — Ba'el
    """

    def __init__(self):
        """Initialize directed Euler."""
        self._adj: Dict[int, List[int]] = defaultdict(list)
        self._in_degree: Dict[int, int] = defaultdict(int)
        self._out_degree: Dict[int, int] = defaultdict(int)
        self._nodes: Set[int] = set()
        self._total_edges = 0
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int) -> None:
        """Add directed edge u → v."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)

            self._adj[u].append(v)
            self._out_degree[u] += 1
            self._in_degree[v] += 1
            self._total_edges += 1

    def _is_connected(self) -> bool:
        """Check if underlying undirected graph is connected."""
        nodes_with_edges = {n for n in self._nodes
                          if self._in_degree[n] > 0 or self._out_degree[n] > 0}

        if not nodes_with_edges:
            return True

        # Build undirected adjacency
        undirected = defaultdict(set)
        for u in self._adj:
            for v in self._adj[u]:
                undirected[u].add(v)
                undirected[v].add(u)

        start = next(iter(nodes_with_edges))
        visited = set()
        stack = [start]

        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)

            for neighbor in undirected[node]:
                if neighbor not in visited:
                    stack.append(neighbor)

        return visited >= nodes_with_edges

    def has_euler_circuit(self) -> bool:
        """Check if Euler circuit exists (in-degree = out-degree for all)."""
        with self._lock:
            if not self._is_connected():
                return False

            for node in self._nodes:
                if self._in_degree[node] != self._out_degree[node]:
                    return False

            return True

    def has_euler_path(self) -> bool:
        """Check if Euler path exists."""
        with self._lock:
            if not self._is_connected():
                return False

            start_count = 0
            end_count = 0

            for node in self._nodes:
                diff = self._out_degree[node] - self._in_degree[node]

                if diff == 1:
                    start_count += 1
                elif diff == -1:
                    end_count += 1
                elif diff != 0:
                    return False

            return (start_count == 0 and end_count == 0) or \
                   (start_count == 1 and end_count == 1)

    def find_euler_circuit(self) -> Optional[List[int]]:
        """Find Euler circuit."""
        with self._lock:
            if not self.has_euler_circuit():
                return None

            if self._total_edges == 0:
                if self._nodes:
                    return [next(iter(self._nodes))]
                return []

            adj = {node: list(neighbors) for node, neighbors in self._adj.items()}

            start = next(n for n in self._nodes if adj.get(n))
            stack = [start]
            circuit = []

            while stack:
                v = stack[-1]

                if adj.get(v):
                    u = adj[v].pop()
                    stack.append(u)
                else:
                    circuit.append(stack.pop())

            return circuit[::-1]

    def find_euler_path(self) -> Optional[List[int]]:
        """Find Euler path."""
        with self._lock:
            if not self.has_euler_path():
                return None

            if self._total_edges == 0:
                if self._nodes:
                    return [next(iter(self._nodes))]
                return []

            # Find start vertex (out-degree - in-degree = 1, or any if circuit)
            start = None

            for node in self._nodes:
                if self._out_degree[node] - self._in_degree[node] == 1:
                    start = node
                    break

            if start is None:
                start = next(n for n in self._nodes if self._adj.get(n))

            adj = {node: list(neighbors) for node, neighbors in self._adj.items()}
            stack = [start]
            path = []

            while stack:
                v = stack[-1]

                if adj.get(v):
                    u = adj[v].pop()
                    stack.append(u)
                else:
                    path.append(stack.pop())

            return path[::-1]

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'node_count': len(self._nodes),
            'edge_count': self._total_edges,
            'is_eulerian': self.has_euler_circuit(),
            'is_semi_eulerian': self.has_euler_path() and not self.has_euler_circuit()
        }


# ============================================================================
# CHINESE POSTMAN PROBLEM
# ============================================================================

class ChinesePostman:
    """
    Chinese Postman Problem solver.

    Find minimum weight closed walk that visits every edge at least once.

    "Ba'el finds the optimal mail route." — Ba'el
    """

    def __init__(self):
        """Initialize Chinese Postman solver."""
        self._adj: Dict[int, List[Tuple[int, float]]] = defaultdict(list)
        self._nodes: Set[int] = set()
        self._total_weight = 0.0
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int, weight: float = 1.0) -> None:
        """Add undirected weighted edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].append((v, weight))
            self._adj[v].append((u, weight))
            self._total_weight += weight

    def _shortest_path(self, start: int, end: int) -> float:
        """Dijkstra's shortest path."""
        import heapq

        dist = {node: float('inf') for node in self._nodes}
        dist[start] = 0
        heap = [(0, start)]

        while heap:
            d, u = heapq.heappop(heap)

            if d > dist[u]:
                continue

            if u == end:
                return dist[end]

            for v, w in self._adj[u]:
                if dist[u] + w < dist[v]:
                    dist[v] = dist[u] + w
                    heapq.heappush(heap, (dist[v], v))

        return dist[end]

    def solve(self) -> float:
        """
        Solve Chinese Postman Problem.

        Returns:
            Minimum total weight to traverse all edges
        """
        with self._lock:
            # Find odd degree vertices
            odd = [n for n in self._nodes if len(self._adj[n]) % 2 != 0]

            if not odd:
                # Already Eulerian
                return self._total_weight

            # Compute pairwise shortest paths between odd vertices
            n = len(odd)
            dist = [[0.0] * n for _ in range(n)]

            for i in range(n):
                for j in range(i + 1, n):
                    d = self._shortest_path(odd[i], odd[j])
                    dist[i][j] = d
                    dist[j][i] = d

            # Minimum weight perfect matching on odd vertices
            # Using DP with bitmask (works for small n)
            if n > 16:
                # Greedy approximation
                used = [False] * n
                extra = 0.0

                while True:
                    best = float('inf')
                    bi, bj = -1, -1

                    for i in range(n):
                        if used[i]:
                            continue
                        for j in range(i + 1, n):
                            if used[j]:
                                continue
                            if dist[i][j] < best:
                                best = dist[i][j]
                                bi, bj = i, j

                    if bi == -1:
                        break

                    used[bi] = True
                    used[bj] = True
                    extra += best

                return self._total_weight + extra

            # DP with bitmask
            INF = float('inf')
            dp = [INF] * (1 << n)
            dp[0] = 0

            for mask in range(1 << n):
                if dp[mask] == INF:
                    continue

                # Find first unset bit
                first = -1
                for i in range(n):
                    if not (mask & (1 << i)):
                        first = i
                        break

                if first == -1:
                    continue

                # Pair with another unset bit
                for j in range(first + 1, n):
                    if not (mask & (1 << j)):
                        new_mask = mask | (1 << first) | (1 << j)
                        dp[new_mask] = min(dp[new_mask], dp[mask] + dist[first][j])

            return self._total_weight + dp[(1 << n) - 1]


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_undirected_euler() -> UndirectedEuler:
    """Create undirected Euler engine."""
    return UndirectedEuler()


def create_directed_euler() -> DirectedEuler:
    """Create directed Euler engine."""
    return DirectedEuler()


def create_chinese_postman() -> ChinesePostman:
    """Create Chinese Postman solver."""
    return ChinesePostman()


def find_euler_circuit_undirected(
    edges: List[Tuple[int, int]]
) -> Optional[List[int]]:
    """Find Euler circuit in undirected graph."""
    engine = UndirectedEuler()
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.find_euler_circuit()


def find_euler_path_undirected(
    edges: List[Tuple[int, int]]
) -> Optional[List[int]]:
    """Find Euler path in undirected graph."""
    engine = UndirectedEuler()
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.find_euler_path()


def find_euler_circuit_directed(
    edges: List[Tuple[int, int]]
) -> Optional[List[int]]:
    """Find Euler circuit in directed graph."""
    engine = DirectedEuler()
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.find_euler_circuit()


def find_euler_path_directed(
    edges: List[Tuple[int, int]]
) -> Optional[List[int]]:
    """Find Euler path in directed graph."""
    engine = DirectedEuler()
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.find_euler_path()


def is_eulerian(edges: List[Tuple[int, int]], directed: bool = False) -> bool:
    """Check if graph has Euler circuit."""
    if directed:
        engine = DirectedEuler()
    else:
        engine = UndirectedEuler()

    for u, v in edges:
        engine.add_edge(u, v)

    return engine.has_euler_circuit()
