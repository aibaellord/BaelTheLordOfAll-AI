"""
BAEL Graph Engine Implementation
==================================

Graph data structures and algorithms.

"Ba'el sees all connections and paths through reality." — Ba'el
"""

import heapq
import logging
import threading
from collections import defaultdict, deque
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger("BAEL.Graph")


# ============================================================================
# ENUMS
# ============================================================================

class GraphType(Enum):
    """Graph types."""
    DIRECTED = "directed"
    UNDIRECTED = "undirected"


class TraversalOrder(Enum):
    """Traversal orders."""
    BFS = "bfs"  # Breadth-first
    DFS = "dfs"  # Depth-first


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Node:
    """A graph node."""
    id: str
    data: Dict[str, Any] = field(default_factory=dict)
    labels: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'data': self.data,
            'labels': list(self.labels)
        }


@dataclass
class Edge:
    """A graph edge."""
    id: str
    source: str
    target: str
    weight: float = 1.0
    edge_type: str = "default"
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'source': self.source,
            'target': self.target,
            'weight': self.weight,
            'type': self.edge_type,
            'data': self.data
        }


@dataclass
class Path:
    """A path in the graph."""
    nodes: List[str]
    edges: List[str]
    total_weight: float = 0.0

    def __len__(self) -> int:
        return len(self.nodes)


# ============================================================================
# GRAPH ENGINE
# ============================================================================

class GraphEngine:
    """
    Graph data structure and algorithms engine.

    Features:
    - Directed/undirected graphs
    - Weighted edges
    - Traversal algorithms
    - Shortest path algorithms
    - Connectivity analysis

    "Ba'el navigates the infinite web of connections." — Ba'el
    """

    def __init__(self, graph_type: GraphType = GraphType.DIRECTED):
        """Initialize graph engine."""
        self.graph_type = graph_type

        # Nodes and edges
        self._nodes: Dict[str, Node] = {}
        self._edges: Dict[str, Edge] = {}

        # Adjacency lists
        self._outgoing: Dict[str, Dict[str, Edge]] = defaultdict(dict)
        self._incoming: Dict[str, Dict[str, Edge]] = defaultdict(dict)

        # Indexes
        self._label_index: Dict[str, Set[str]] = defaultdict(set)
        self._type_index: Dict[str, Set[str]] = defaultdict(set)

        # Thread safety
        self._lock = threading.RLock()

        # Stats
        self._stats = {
            'nodes_added': 0,
            'edges_added': 0,
            'traversals': 0,
            'path_searches': 0
        }

        logger.info(f"Graph engine initialized ({graph_type.value})")

    # ========================================================================
    # NODE OPERATIONS
    # ========================================================================

    def add_node(
        self,
        node_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        labels: Optional[Set[str]] = None
    ) -> Node:
        """Add a node."""
        node_id = node_id or str(uuid.uuid4())

        node = Node(
            id=node_id,
            data=data or {},
            labels=labels or set()
        )

        with self._lock:
            self._nodes[node_id] = node

            # Update label index
            for label in node.labels:
                self._label_index[label].add(node_id)

            self._stats['nodes_added'] += 1

        return node

    def get_node(self, node_id: str) -> Optional[Node]:
        """Get node by ID."""
        return self._nodes.get(node_id)

    def update_node(
        self,
        node_id: str,
        data: Optional[Dict[str, Any]] = None,
        labels: Optional[Set[str]] = None
    ) -> Optional[Node]:
        """Update a node."""
        node = self._nodes.get(node_id)
        if not node:
            return None

        with self._lock:
            if data:
                node.data.update(data)

            if labels:
                # Remove old labels from index
                for label in node.labels:
                    self._label_index[label].discard(node_id)

                # Set new labels
                node.labels = labels

                # Update index
                for label in labels:
                    self._label_index[label].add(node_id)

        return node

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and its edges."""
        with self._lock:
            if node_id not in self._nodes:
                return False

            # Remove edges
            for target_id, edge in list(self._outgoing[node_id].items()):
                self._remove_edge_internal(edge.id)

            for source_id, edge in list(self._incoming[node_id].items()):
                self._remove_edge_internal(edge.id)

            # Remove from indexes
            node = self._nodes[node_id]
            for label in node.labels:
                self._label_index[label].discard(node_id)

            del self._nodes[node_id]
            del self._outgoing[node_id]
            del self._incoming[node_id]

        return True

    def get_nodes_by_label(self, label: str) -> List[Node]:
        """Get nodes with a label."""
        node_ids = self._label_index.get(label, set())
        return [self._nodes[nid] for nid in node_ids if nid in self._nodes]

    # ========================================================================
    # EDGE OPERATIONS
    # ========================================================================

    def add_edge(
        self,
        source: str,
        target: str,
        weight: float = 1.0,
        edge_type: str = "default",
        data: Optional[Dict[str, Any]] = None,
        edge_id: Optional[str] = None
    ) -> Edge:
        """Add an edge."""
        edge_id = edge_id or str(uuid.uuid4())

        edge = Edge(
            id=edge_id,
            source=source,
            target=target,
            weight=weight,
            edge_type=edge_type,
            data=data or {}
        )

        with self._lock:
            # Ensure nodes exist
            if source not in self._nodes:
                self.add_node(source)
            if target not in self._nodes:
                self.add_node(target)

            self._edges[edge_id] = edge
            self._outgoing[source][target] = edge
            self._incoming[target][source] = edge

            # For undirected, add reverse
            if self.graph_type == GraphType.UNDIRECTED:
                reverse_edge = Edge(
                    id=f"{edge_id}_reverse",
                    source=target,
                    target=source,
                    weight=weight,
                    edge_type=edge_type,
                    data=data or {}
                )
                self._edges[reverse_edge.id] = reverse_edge
                self._outgoing[target][source] = reverse_edge
                self._incoming[source][target] = reverse_edge

            # Update type index
            self._type_index[edge_type].add(edge_id)

            self._stats['edges_added'] += 1

        return edge

    def get_edge(
        self,
        source: str,
        target: str
    ) -> Optional[Edge]:
        """Get edge between nodes."""
        return self._outgoing.get(source, {}).get(target)

    def remove_edge(
        self,
        source: str,
        target: str
    ) -> bool:
        """Remove edge between nodes."""
        edge = self.get_edge(source, target)
        if not edge:
            return False

        return self._remove_edge_internal(edge.id)

    def _remove_edge_internal(self, edge_id: str) -> bool:
        """Remove edge by ID."""
        with self._lock:
            edge = self._edges.get(edge_id)
            if not edge:
                return False

            del self._edges[edge_id]

            if edge.target in self._outgoing.get(edge.source, {}):
                del self._outgoing[edge.source][edge.target]

            if edge.source in self._incoming.get(edge.target, {}):
                del self._incoming[edge.target][edge.source]

            self._type_index[edge.edge_type].discard(edge_id)

        return True

    def get_neighbors(
        self,
        node_id: str,
        direction: str = "outgoing"
    ) -> List[str]:
        """Get neighbor node IDs."""
        if direction == "outgoing":
            return list(self._outgoing.get(node_id, {}).keys())
        elif direction == "incoming":
            return list(self._incoming.get(node_id, {}).keys())
        else:
            outgoing = set(self._outgoing.get(node_id, {}).keys())
            incoming = set(self._incoming.get(node_id, {}).keys())
            return list(outgoing | incoming)

    # ========================================================================
    # TRAVERSAL
    # ========================================================================

    def traverse(
        self,
        start: str,
        order: TraversalOrder = TraversalOrder.BFS,
        max_depth: Optional[int] = None
    ) -> Generator[Tuple[str, int], None, None]:
        """
        Traverse graph from starting node.

        Yields:
            (node_id, depth) tuples
        """
        if start not in self._nodes:
            return

        self._stats['traversals'] += 1

        visited = set()

        if order == TraversalOrder.BFS:
            yield from self._bfs(start, visited, max_depth)
        else:
            yield from self._dfs(start, visited, max_depth, 0)

    def _bfs(
        self,
        start: str,
        visited: Set[str],
        max_depth: Optional[int]
    ) -> Generator[Tuple[str, int], None, None]:
        """Breadth-first traversal."""
        queue = deque([(start, 0)])
        visited.add(start)

        while queue:
            node_id, depth = queue.popleft()
            yield node_id, depth

            if max_depth is not None and depth >= max_depth:
                continue

            for neighbor in self.get_neighbors(node_id):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))

    def _dfs(
        self,
        node_id: str,
        visited: Set[str],
        max_depth: Optional[int],
        depth: int
    ) -> Generator[Tuple[str, int], None, None]:
        """Depth-first traversal."""
        if node_id in visited:
            return

        if max_depth is not None and depth > max_depth:
            return

        visited.add(node_id)
        yield node_id, depth

        for neighbor in self.get_neighbors(node_id):
            yield from self._dfs(neighbor, visited, max_depth, depth + 1)

    # ========================================================================
    # SHORTEST PATH ALGORITHMS
    # ========================================================================

    def shortest_path(
        self,
        source: str,
        target: str,
        algorithm: str = "dijkstra"
    ) -> Optional[Path]:
        """
        Find shortest path between nodes.

        Args:
            source: Source node
            target: Target node
            algorithm: "dijkstra" or "bfs"

        Returns:
            Path or None
        """
        self._stats['path_searches'] += 1

        if source not in self._nodes or target not in self._nodes:
            return None

        if algorithm == "dijkstra":
            return self._dijkstra(source, target)
        else:
            return self._bfs_path(source, target)

    def _dijkstra(
        self,
        source: str,
        target: str
    ) -> Optional[Path]:
        """Dijkstra's shortest path algorithm."""
        distances = {source: 0.0}
        previous = {}
        previous_edge = {}
        pq = [(0.0, source)]
        visited = set()

        while pq:
            dist, node = heapq.heappop(pq)

            if node in visited:
                continue

            visited.add(node)

            if node == target:
                break

            for neighbor, edge in self._outgoing.get(node, {}).items():
                if neighbor in visited:
                    continue

                new_dist = dist + edge.weight

                if neighbor not in distances or new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    previous[neighbor] = node
                    previous_edge[neighbor] = edge.id
                    heapq.heappush(pq, (new_dist, neighbor))

        if target not in previous and source != target:
            return None

        # Reconstruct path
        path_nodes = []
        path_edges = []
        current = target

        while current is not None:
            path_nodes.append(current)
            if current in previous_edge:
                path_edges.append(previous_edge[current])
            current = previous.get(current)

        path_nodes.reverse()
        path_edges.reverse()

        return Path(
            nodes=path_nodes,
            edges=path_edges,
            total_weight=distances.get(target, 0.0)
        )

    def _bfs_path(
        self,
        source: str,
        target: str
    ) -> Optional[Path]:
        """BFS shortest path (unweighted)."""
        if source == target:
            return Path(nodes=[source], edges=[], total_weight=0)

        queue = deque([(source, [source], [])])
        visited = {source}

        while queue:
            node, path, edges = queue.popleft()

            for neighbor, edge in self._outgoing.get(node, {}).items():
                if neighbor == target:
                    return Path(
                        nodes=path + [neighbor],
                        edges=edges + [edge.id],
                        total_weight=len(path)
                    )

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((
                        neighbor,
                        path + [neighbor],
                        edges + [edge.id]
                    ))

        return None

    def all_shortest_paths(
        self,
        source: str
    ) -> Dict[str, Path]:
        """Find shortest paths from source to all nodes."""
        paths = {}

        for node_id in self._nodes:
            if node_id != source:
                path = self.shortest_path(source, node_id)
                if path:
                    paths[node_id] = path

        return paths

    # ========================================================================
    # CONNECTIVITY
    # ========================================================================

    def is_connected(
        self,
        source: str,
        target: str
    ) -> bool:
        """Check if path exists between nodes."""
        if source not in self._nodes or target not in self._nodes:
            return False

        visited = set()
        queue = deque([source])

        while queue:
            node = queue.popleft()

            if node == target:
                return True

            if node in visited:
                continue

            visited.add(node)

            for neighbor in self.get_neighbors(node):
                if neighbor not in visited:
                    queue.append(neighbor)

        return False

    def connected_components(self) -> List[Set[str]]:
        """Find connected components."""
        visited = set()
        components = []

        for node_id in self._nodes:
            if node_id not in visited:
                component = set()

                queue = deque([node_id])
                while queue:
                    node = queue.popleft()
                    if node in visited:
                        continue

                    visited.add(node)
                    component.add(node)

                    for neighbor in self.get_neighbors(node, "both"):
                        if neighbor not in visited:
                            queue.append(neighbor)

                components.append(component)

        return components

    def find_cycles(self) -> List[List[str]]:
        """Find cycles in the graph."""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.get_neighbors(node):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])

            path.pop()
            rec_stack.remove(node)

        for node_id in self._nodes:
            if node_id not in visited:
                dfs(node_id, [])

        return cycles

    # ========================================================================
    # ANALYTICS
    # ========================================================================

    def degree(self, node_id: str) -> Dict[str, int]:
        """Get node degree."""
        return {
            'in': len(self._incoming.get(node_id, {})),
            'out': len(self._outgoing.get(node_id, {})),
            'total': len(self._incoming.get(node_id, {})) +
                     len(self._outgoing.get(node_id, {}))
        }

    def pagerank(
        self,
        damping: float = 0.85,
        iterations: int = 100
    ) -> Dict[str, float]:
        """Calculate PageRank."""
        n = len(self._nodes)
        if n == 0:
            return {}

        ranks = {node_id: 1.0 / n for node_id in self._nodes}

        for _ in range(iterations):
            new_ranks = {}

            for node_id in self._nodes:
                rank = (1 - damping) / n

                for source_id in self._incoming.get(node_id, {}):
                    out_degree = len(self._outgoing.get(source_id, {}))
                    if out_degree > 0:
                        rank += damping * ranks[source_id] / out_degree

                new_ranks[node_id] = rank

            ranks = new_ranks

        return ranks

    # ========================================================================
    # QUERIES
    # ========================================================================

    def node_count(self) -> int:
        """Get number of nodes."""
        return len(self._nodes)

    def edge_count(self) -> int:
        """Get number of edges."""
        return len(self._edges)

    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            'nodes': len(self._nodes),
            'edges': len(self._edges),
            'type': self.graph_type.value,
            **self._stats
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

graph_engine: Optional[GraphEngine] = None


def get_graph(
    graph_type: GraphType = GraphType.DIRECTED
) -> GraphEngine:
    """Get or create graph engine."""
    global graph_engine
    if graph_engine is None:
        graph_engine = GraphEngine(graph_type)
    return graph_engine


def create_graph(
    graph_type: GraphType = GraphType.DIRECTED
) -> GraphEngine:
    """Create new graph engine."""
    return GraphEngine(graph_type)
