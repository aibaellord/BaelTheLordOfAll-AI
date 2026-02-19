"""
BAEL Network Flow Engine
========================

Maximum flow algorithms.

"Ba'el maximizes the flow of power." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque

logger = logging.getLogger("BAEL.NetworkFlow")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class FlowStats:
    """Flow statistics."""
    node_count: int = 0
    edge_count: int = 0
    max_flow: float = 0.0
    iterations: int = 0


# ============================================================================
# DINIC'S ALGORITHM
# ============================================================================

class DinicFlow:
    """
    Dinic's algorithm for maximum flow.

    Features:
    - O(V²E) complexity
    - O(E√V) for unit capacity
    - Blocking flow approach

    "Ba'el finds flow through levels." — Ba'el
    """

    def __init__(self):
        """Initialize Dinic's algorithm."""
        self._adj: Dict[int, Dict[int, float]] = defaultdict(lambda: defaultdict(float))
        self._nodes: Set[int] = set()
        self._edge_count = 0
        self._stats = FlowStats()
        self._lock = threading.RLock()

        logger.debug("Dinic flow initialized")

    def add_edge(self, u: int, v: int, capacity: float) -> None:
        """Add directed edge with capacity."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u][v] += capacity
            self._edge_count += 1

            # Initialize reverse edge if not exists
            if v not in self._adj or u not in self._adj[v]:
                self._adj[v][u] = 0

    def _bfs(self, source: int, sink: int, level: Dict[int, int]) -> bool:
        """BFS to build level graph."""
        level.clear()
        level[source] = 0
        queue = deque([source])

        while queue:
            u = queue.popleft()

            for v, cap in self._adj[u].items():
                if v not in level and cap > 0:
                    level[v] = level[u] + 1
                    queue.append(v)

        return sink in level

    def _dfs(
        self,
        u: int,
        sink: int,
        pushed: float,
        level: Dict[int, int],
        iter_: Dict[int, int]
    ) -> float:
        """DFS to find blocking flow."""
        if u == sink:
            return pushed

        neighbors = list(self._adj[u].keys())

        while iter_[u] < len(neighbors):
            v = neighbors[iter_[u]]

            if level.get(v, -1) == level[u] + 1 and self._adj[u][v] > 0:
                d = self._dfs(v, sink, min(pushed, self._adj[u][v]), level, iter_)

                if d > 0:
                    self._adj[u][v] -= d
                    self._adj[v][u] += d
                    return d

            iter_[u] += 1

        return 0

    def max_flow(self, source: int, sink: int) -> float:
        """
        Compute maximum flow from source to sink.

        Returns:
            Maximum flow value
        """
        with self._lock:
            if source == sink:
                return 0

            # Make working copy
            adj = defaultdict(lambda: defaultdict(float))
            for u in self._adj:
                for v, cap in self._adj[u].items():
                    adj[u][v] = cap

            # Temporarily replace
            original = self._adj
            self._adj = adj

            flow = 0.0
            level = {}
            iterations = 0

            while self._bfs(source, sink, level):
                iter_ = {node: 0 for node in self._nodes}

                while True:
                    pushed = self._dfs(source, sink, float('inf'), level, iter_)
                    if pushed == 0:
                        break
                    flow += pushed

                iterations += 1

            # Restore original
            self._adj = original

            self._stats.node_count = len(self._nodes)
            self._stats.edge_count = self._edge_count
            self._stats.max_flow = flow
            self._stats.iterations = iterations

            logger.info(f"Dinic max flow: {flow}")
            return flow

    def get_min_cut(self, source: int, sink: int) -> Tuple[Set[int], Set[int]]:
        """
        Get minimum cut (S, T) partition.

        Returns:
            (S, T) where S contains source, T contains sink
        """
        with self._lock:
            # Run max flow first
            self.max_flow(source, sink)

            # BFS from source on residual graph
            visited = set()
            queue = deque([source])
            visited.add(source)

            while queue:
                u = queue.popleft()

                for v, cap in self._adj[u].items():
                    if v not in visited and cap > 0:
                        visited.add(v)
                        queue.append(v)

            s_side = visited
            t_side = self._nodes - visited

            return s_side, t_side

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'node_count': self._stats.node_count,
            'edge_count': self._stats.edge_count,
            'max_flow': self._stats.max_flow,
            'iterations': self._stats.iterations
        }


# ============================================================================
# PUSH-RELABEL ALGORITHM
# ============================================================================

class PushRelabelFlow:
    """
    Push-Relabel algorithm for maximum flow.

    Features:
    - O(V²E) complexity
    - O(V³) with FIFO selection
    - Preflow-push approach

    "Ba'el pushes excess to the sink." — Ba'el
    """

    def __init__(self):
        """Initialize Push-Relabel."""
        self._capacity: Dict[int, Dict[int, float]] = defaultdict(lambda: defaultdict(float))
        self._nodes: Set[int] = set()
        self._edge_count = 0
        self._stats = FlowStats()
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int, capacity: float) -> None:
        """Add directed edge with capacity."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._capacity[u][v] += capacity
            self._edge_count += 1

    def max_flow(self, source: int, sink: int) -> float:
        """
        Compute maximum flow using Push-Relabel.

        Returns:
            Maximum flow value
        """
        with self._lock:
            if source == sink:
                return 0

            n = len(self._nodes)
            node_list = list(self._nodes)
            idx = {node: i for i, node in enumerate(node_list)}

            # Initialize
            height = {node: 0 for node in self._nodes}
            height[source] = n

            excess = {node: 0.0 for node in self._nodes}

            flow = defaultdict(lambda: defaultdict(float))

            # Preflow from source
            for v, cap in self._capacity[source].items():
                flow[source][v] = cap
                flow[v][source] = -cap
                excess[v] = cap
                excess[source] -= cap

            # Active vertices (have excess, not source or sink)
            active = deque([v for v in self._nodes
                          if v != source and v != sink and excess[v] > 0])

            iterations = 0

            while active:
                u = active[0]
                pushed = False

                for v in self._nodes:
                    residual = self._capacity[u][v] - flow[u][v]

                    if residual > 0 and height[u] == height[v] + 1:
                        # Push
                        push_amount = min(excess[u], residual)
                        flow[u][v] += push_amount
                        flow[v][u] -= push_amount
                        excess[u] -= push_amount
                        excess[v] += push_amount

                        if v != source and v != sink and excess[v] == push_amount:
                            active.append(v)

                        if excess[u] == 0:
                            active.popleft()
                            pushed = True
                            break

                if not pushed:
                    # Relabel
                    min_height = float('inf')

                    for v in self._nodes:
                        if self._capacity[u][v] - flow[u][v] > 0:
                            min_height = min(min_height, height[v])

                    if min_height < float('inf'):
                        height[u] = min_height + 1
                    else:
                        active.popleft()

                iterations += 1

                if iterations > n * n * self._edge_count:
                    break

            max_flow_value = sum(flow[source][v] for v in self._capacity[source])

            self._stats.node_count = n
            self._stats.edge_count = self._edge_count
            self._stats.max_flow = max_flow_value
            self._stats.iterations = iterations

            logger.info(f"Push-Relabel max flow: {max_flow_value}")
            return max_flow_value


# ============================================================================
# FORD-FULKERSON (EDMONDS-KARP)
# ============================================================================

class EdmondsKarpFlow:
    """
    Edmonds-Karp algorithm (Ford-Fulkerson with BFS).

    Features:
    - O(VE²) complexity
    - Simple BFS augmenting paths

    "Ba'el finds the shortest augmenting path." — Ba'el
    """

    def __init__(self):
        """Initialize Edmonds-Karp."""
        self._capacity: Dict[int, Dict[int, float]] = defaultdict(lambda: defaultdict(float))
        self._nodes: Set[int] = set()
        self._edge_count = 0
        self._stats = FlowStats()
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int, capacity: float) -> None:
        """Add directed edge with capacity."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._capacity[u][v] += capacity
            self._edge_count += 1

    def _bfs(
        self,
        source: int,
        sink: int,
        parent: Dict[int, int],
        residual: Dict[int, Dict[int, float]]
    ) -> bool:
        """Find augmenting path using BFS."""
        visited = {source}
        queue = deque([source])

        while queue:
            u = queue.popleft()

            for v in self._nodes:
                if v not in visited and residual[u][v] > 0:
                    visited.add(v)
                    parent[v] = u

                    if v == sink:
                        return True

                    queue.append(v)

        return False

    def max_flow(self, source: int, sink: int) -> float:
        """Compute maximum flow."""
        with self._lock:
            if source == sink:
                return 0

            # Initialize residual graph
            residual = defaultdict(lambda: defaultdict(float))
            for u in self._capacity:
                for v, cap in self._capacity[u].items():
                    residual[u][v] = cap

            max_flow_value = 0.0
            parent = {}
            iterations = 0

            while self._bfs(source, sink, parent, residual):
                # Find minimum residual on path
                path_flow = float('inf')
                v = sink

                while v != source:
                    u = parent[v]
                    path_flow = min(path_flow, residual[u][v])
                    v = u

                # Update residual graph
                v = sink
                while v != source:
                    u = parent[v]
                    residual[u][v] -= path_flow
                    residual[v][u] += path_flow
                    v = u

                max_flow_value += path_flow
                parent.clear()
                iterations += 1

            self._stats.node_count = len(self._nodes)
            self._stats.edge_count = self._edge_count
            self._stats.max_flow = max_flow_value
            self._stats.iterations = iterations

            return max_flow_value


# ============================================================================
# MINIMUM COST MAXIMUM FLOW
# ============================================================================

class MinCostMaxFlow:
    """
    Minimum cost maximum flow using SPFA.

    "Ba'el maximizes flow at minimum cost." — Ba'el
    """

    def __init__(self):
        """Initialize min-cost max-flow."""
        self._edges: List[Tuple[int, int, float, float]] = []  # (u, v, cap, cost)
        self._nodes: Set[int] = set()
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int, capacity: float, cost: float) -> None:
        """Add edge with capacity and cost."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._edges.append((u, v, capacity, cost))

    def solve(self, source: int, sink: int) -> Tuple[float, float]:
        """
        Compute minimum cost maximum flow.

        Returns:
            (max_flow, min_cost)
        """
        with self._lock:
            # Build adjacency with indices
            graph = defaultdict(list)
            edge_data = []  # (to, rev_idx, cap, cost)

            for u, v, cap, cost in self._edges:
                rev_idx_v = len(graph[v])
                rev_idx_u = len(graph[u])

                graph[u].append([v, rev_idx_v, cap, cost])
                graph[v].append([u, rev_idx_u, 0, -cost])  # Reverse edge

            INF = float('inf')
            total_flow = 0.0
            total_cost = 0.0

            while True:
                # SPFA to find shortest path
                dist = {node: INF for node in self._nodes}
                dist[source] = 0
                in_queue = {node: False for node in self._nodes}
                in_queue[source] = True
                prev_node = {}
                prev_edge = {}

                queue = deque([source])

                while queue:
                    u = queue.popleft()
                    in_queue[u] = False

                    for i, (v, rev_idx, cap, cost) in enumerate(graph[u]):
                        if cap > 0 and dist[u] + cost < dist[v]:
                            dist[v] = dist[u] + cost
                            prev_node[v] = u
                            prev_edge[v] = (i, rev_idx)

                            if not in_queue[v]:
                                in_queue[v] = True
                                queue.append(v)

                if dist[sink] == INF:
                    break

                # Find minimum flow on path
                path_flow = INF
                v = sink

                while v != source:
                    u = prev_node[v]
                    edge_idx, _ = prev_edge[v]
                    path_flow = min(path_flow, graph[u][edge_idx][2])
                    v = u

                # Update flow
                v = sink
                while v != source:
                    u = prev_node[v]
                    edge_idx, rev_idx = prev_edge[v]

                    graph[u][edge_idx][2] -= path_flow
                    graph[v][rev_idx][2] += path_flow
                    v = u

                total_flow += path_flow
                total_cost += path_flow * dist[sink]

            return total_flow, total_cost


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_dinic_flow() -> DinicFlow:
    """Create Dinic flow engine."""
    return DinicFlow()


def create_push_relabel_flow() -> PushRelabelFlow:
    """Create Push-Relabel flow engine."""
    return PushRelabelFlow()


def create_edmonds_karp_flow() -> EdmondsKarpFlow:
    """Create Edmonds-Karp flow engine."""
    return EdmondsKarpFlow()


def create_min_cost_flow() -> MinCostMaxFlow:
    """Create min-cost max-flow engine."""
    return MinCostMaxFlow()


def max_flow(
    edges: List[Tuple[int, int, float]],
    source: int,
    sink: int,
    algorithm: str = "dinic"
) -> float:
    """
    Compute maximum flow.

    Args:
        edges: List of (u, v, capacity)
        source: Source vertex
        sink: Sink vertex
        algorithm: "dinic", "push_relabel", or "edmonds_karp"

    Returns:
        Maximum flow value
    """
    if algorithm == "push_relabel":
        engine = PushRelabelFlow()
    elif algorithm == "edmonds_karp":
        engine = EdmondsKarpFlow()
    else:
        engine = DinicFlow()

    for u, v, cap in edges:
        engine.add_edge(u, v, cap)

    return engine.max_flow(source, sink)


def min_cut(
    edges: List[Tuple[int, int, float]],
    source: int,
    sink: int
) -> Tuple[Set[int], Set[int]]:
    """Find minimum cut partition."""
    engine = DinicFlow()
    for u, v, cap in edges:
        engine.add_edge(u, v, cap)
    return engine.get_min_cut(source, sink)


def min_cost_max_flow(
    edges: List[Tuple[int, int, float, float]],
    source: int,
    sink: int
) -> Tuple[float, float]:
    """
    Compute minimum cost maximum flow.

    Args:
        edges: List of (u, v, capacity, cost)
        source: Source vertex
        sink: Sink vertex

    Returns:
        (max_flow, min_cost)
    """
    engine = MinCostMaxFlow()
    for u, v, cap, cost in edges:
        engine.add_edge(u, v, cap, cost)
    return engine.solve(source, sink)
