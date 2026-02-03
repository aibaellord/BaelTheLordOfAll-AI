#!/usr/bin/env python3
"""
BAEL - Graph Manager
Advanced graph data structures and algorithms for AI agent operations.

Features:
- Directed/undirected graphs
- Weighted edges
- Graph traversal (BFS, DFS)
- Shortest path algorithms
- Topological sorting
- Cycle detection
- Connected components
- Graph visualization
- Subgraph extraction
- Path finding
"""

import asyncio
import collections
import heapq
import json
import threading
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, TypeVar, Union)

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


# =============================================================================
# ENUMS
# =============================================================================

class GraphType(Enum):
    """Graph types."""
    DIRECTED = "directed"
    UNDIRECTED = "undirected"
    DAG = "dag"  # Directed Acyclic Graph


class TraversalOrder(Enum):
    """Traversal order types."""
    BFS = "bfs"
    DFS = "dfs"
    DFS_PREORDER = "dfs_preorder"
    DFS_POSTORDER = "dfs_postorder"


class EdgeType(Enum):
    """Edge types."""
    TREE = "tree"
    BACK = "back"
    FORWARD = "forward"
    CROSS = "cross"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Node(Generic[T]):
    """A node in the graph."""
    node_id: str
    data: Optional[T] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Edge:
    """An edge in the graph."""
    edge_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = ""
    target: str = ""
    weight: float = 1.0
    label: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Path:
    """A path through the graph."""
    nodes: List[str] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    total_weight: float = 0.0

    def __len__(self) -> int:
        return len(self.nodes)

    def is_empty(self) -> bool:
        return len(self.nodes) == 0


@dataclass
class GraphStats:
    """Graph statistics."""
    node_count: int = 0
    edge_count: int = 0
    density: float = 0.0
    is_connected: bool = False
    has_cycles: bool = False
    components: int = 0


@dataclass
class TraversalResult:
    """Result of graph traversal."""
    visited: List[str] = field(default_factory=list)
    discovery_time: Dict[str, int] = field(default_factory=dict)
    finish_time: Dict[str, int] = field(default_factory=dict)
    parents: Dict[str, Optional[str]] = field(default_factory=dict)


# =============================================================================
# GRAPH IMPLEMENTATIONS
# =============================================================================

class Graph(Generic[T]):
    """
    A graph data structure.
    """

    def __init__(
        self,
        graph_type: GraphType = GraphType.DIRECTED
    ):
        self.graph_id = str(uuid.uuid4())
        self.graph_type = graph_type

        self._nodes: Dict[str, Node[T]] = {}
        self._adjacency: Dict[str, Dict[str, Edge]] = defaultdict(dict)
        self._reverse_adjacency: Dict[str, Dict[str, Edge]] = defaultdict(dict)

        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # NODE OPERATIONS
    # -------------------------------------------------------------------------

    def add_node(
        self,
        node_id: str,
        data: Optional[T] = None,
        **metadata
    ) -> Node[T]:
        """Add a node to the graph."""
        with self._lock:
            node = Node(
                node_id=node_id,
                data=data,
                metadata=metadata
            )
            self._nodes[node_id] = node
            return node

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and its edges."""
        with self._lock:
            if node_id not in self._nodes:
                return False

            # Remove outgoing edges
            if node_id in self._adjacency:
                for target in list(self._adjacency[node_id].keys()):
                    if target in self._reverse_adjacency:
                        self._reverse_adjacency[target].pop(node_id, None)
                del self._adjacency[node_id]

            # Remove incoming edges
            if node_id in self._reverse_adjacency:
                for source in list(self._reverse_adjacency[node_id].keys()):
                    if source in self._adjacency:
                        self._adjacency[source].pop(node_id, None)
                del self._reverse_adjacency[node_id]

            del self._nodes[node_id]
            return True

    def get_node(self, node_id: str) -> Optional[Node[T]]:
        """Get a node by ID."""
        with self._lock:
            return self._nodes.get(node_id)

    def has_node(self, node_id: str) -> bool:
        """Check if node exists."""
        with self._lock:
            return node_id in self._nodes

    def get_nodes(self) -> List[Node[T]]:
        """Get all nodes."""
        with self._lock:
            return list(self._nodes.values())

    def node_count(self) -> int:
        """Get node count."""
        with self._lock:
            return len(self._nodes)

    # -------------------------------------------------------------------------
    # EDGE OPERATIONS
    # -------------------------------------------------------------------------

    def add_edge(
        self,
        source: str,
        target: str,
        weight: float = 1.0,
        label: Optional[str] = None,
        **metadata
    ) -> Optional[Edge]:
        """Add an edge to the graph."""
        with self._lock:
            # Auto-create nodes if needed
            if source not in self._nodes:
                self.add_node(source)
            if target not in self._nodes:
                self.add_node(target)

            # Check for DAG constraints
            if self.graph_type == GraphType.DAG:
                if self._would_create_cycle(source, target):
                    return None

            edge = Edge(
                source=source,
                target=target,
                weight=weight,
                label=label,
                metadata=metadata
            )

            self._adjacency[source][target] = edge
            self._reverse_adjacency[target][source] = edge

            # For undirected graphs, add reverse edge
            if self.graph_type == GraphType.UNDIRECTED:
                reverse = Edge(
                    source=target,
                    target=source,
                    weight=weight,
                    label=label,
                    metadata=metadata
                )
                self._adjacency[target][source] = reverse
                self._reverse_adjacency[source][target] = reverse

            return edge

    def remove_edge(self, source: str, target: str) -> bool:
        """Remove an edge."""
        with self._lock:
            if source not in self._adjacency:
                return False
            if target not in self._adjacency[source]:
                return False

            del self._adjacency[source][target]
            if target in self._reverse_adjacency:
                self._reverse_adjacency[target].pop(source, None)

            # For undirected, remove reverse
            if self.graph_type == GraphType.UNDIRECTED:
                if target in self._adjacency:
                    self._adjacency[target].pop(source, None)
                if source in self._reverse_adjacency:
                    self._reverse_adjacency[source].pop(target, None)

            return True

    def get_edge(self, source: str, target: str) -> Optional[Edge]:
        """Get an edge."""
        with self._lock:
            return self._adjacency.get(source, {}).get(target)

    def has_edge(self, source: str, target: str) -> bool:
        """Check if edge exists."""
        with self._lock:
            return target in self._adjacency.get(source, {})

    def get_edges(self) -> List[Edge]:
        """Get all edges."""
        with self._lock:
            edges = []
            for source, targets in self._adjacency.items():
                for edge in targets.values():
                    edges.append(edge)
            return edges

    def edge_count(self) -> int:
        """Get edge count."""
        with self._lock:
            count = sum(len(t) for t in self._adjacency.values())
            if self.graph_type == GraphType.UNDIRECTED:
                count //= 2
            return count

    # -------------------------------------------------------------------------
    # NEIGHBORS
    # -------------------------------------------------------------------------

    def get_neighbors(self, node_id: str) -> List[str]:
        """Get outgoing neighbors."""
        with self._lock:
            return list(self._adjacency.get(node_id, {}).keys())

    def get_predecessors(self, node_id: str) -> List[str]:
        """Get incoming neighbors."""
        with self._lock:
            return list(self._reverse_adjacency.get(node_id, {}).keys())

    def get_degree(self, node_id: str) -> int:
        """Get node degree (out-degree for directed)."""
        with self._lock:
            return len(self._adjacency.get(node_id, {}))

    def get_in_degree(self, node_id: str) -> int:
        """Get in-degree."""
        with self._lock:
            return len(self._reverse_adjacency.get(node_id, {}))

    def get_out_degree(self, node_id: str) -> int:
        """Get out-degree."""
        return self.get_degree(node_id)

    # -------------------------------------------------------------------------
    # CYCLE DETECTION
    # -------------------------------------------------------------------------

    def _would_create_cycle(self, source: str, target: str) -> bool:
        """Check if adding edge would create cycle."""
        # DFS from target to see if we can reach source
        visited = set()
        stack = [target]

        while stack:
            current = stack.pop()
            if current == source:
                return True

            if current not in visited:
                visited.add(current)
                stack.extend(self._adjacency.get(current, {}).keys())

        return False

    def has_cycle(self) -> bool:
        """Check if graph has a cycle."""
        with self._lock:
            if self.graph_type == GraphType.DAG:
                return False

            visited = set()
            rec_stack = set()

            def dfs(node: str) -> bool:
                visited.add(node)
                rec_stack.add(node)

                for neighbor in self._adjacency.get(node, {}):
                    if neighbor not in visited:
                        if dfs(neighbor):
                            return True
                    elif neighbor in rec_stack:
                        return True

                rec_stack.remove(node)
                return False

            for node in self._nodes:
                if node not in visited:
                    if dfs(node):
                        return True

            return False

    def find_cycles(self) -> List[List[str]]:
        """Find all cycles in the graph."""
        with self._lock:
            cycles = []
            visited = set()
            rec_stack = []
            rec_set = set()

            def dfs(node: str) -> None:
                visited.add(node)
                rec_stack.append(node)
                rec_set.add(node)

                for neighbor in self._adjacency.get(node, {}):
                    if neighbor not in visited:
                        dfs(neighbor)
                    elif neighbor in rec_set:
                        # Found cycle
                        idx = rec_stack.index(neighbor)
                        cycle = rec_stack[idx:] + [neighbor]
                        cycles.append(cycle)

                rec_stack.pop()
                rec_set.remove(node)

            for node in self._nodes:
                if node not in visited:
                    dfs(node)

            return cycles

    # -------------------------------------------------------------------------
    # TRAVERSAL
    # -------------------------------------------------------------------------

    def bfs(
        self,
        start: str,
        visit: Optional[Callable[[str, Optional[T]], None]] = None
    ) -> TraversalResult:
        """Breadth-first search."""
        with self._lock:
            result = TraversalResult()

            if start not in self._nodes:
                return result

            visited = set()
            queue = deque([start])
            time_counter = 0

            while queue:
                node_id = queue.popleft()

                if node_id in visited:
                    continue

                visited.add(node_id)
                result.visited.append(node_id)
                result.discovery_time[node_id] = time_counter
                time_counter += 1

                if visit:
                    node = self._nodes.get(node_id)
                    visit(node_id, node.data if node else None)

                for neighbor in self._adjacency.get(node_id, {}):
                    if neighbor not in visited:
                        if neighbor not in result.parents:
                            result.parents[neighbor] = node_id
                        queue.append(neighbor)

            return result

    def dfs(
        self,
        start: str,
        visit: Optional[Callable[[str, Optional[T]], None]] = None,
        order: TraversalOrder = TraversalOrder.DFS_PREORDER
    ) -> TraversalResult:
        """Depth-first search."""
        with self._lock:
            result = TraversalResult()

            if start not in self._nodes:
                return result

            visited = set()
            time_counter = [0]

            def dfs_visit(node_id: str) -> None:
                if node_id in visited:
                    return

                visited.add(node_id)
                result.discovery_time[node_id] = time_counter[0]
                time_counter[0] += 1

                if order == TraversalOrder.DFS_PREORDER and visit:
                    node = self._nodes.get(node_id)
                    visit(node_id, node.data if node else None)

                result.visited.append(node_id)

                for neighbor in self._adjacency.get(node_id, {}):
                    if neighbor not in visited:
                        result.parents[neighbor] = node_id
                        dfs_visit(neighbor)

                result.finish_time[node_id] = time_counter[0]
                time_counter[0] += 1

                if order == TraversalOrder.DFS_POSTORDER and visit:
                    node = self._nodes.get(node_id)
                    visit(node_id, node.data if node else None)

            dfs_visit(start)
            return result

    def dfs_iterative(self, start: str) -> List[str]:
        """Iterative DFS."""
        with self._lock:
            if start not in self._nodes:
                return []

            visited = []
            seen = set()
            stack = [start]

            while stack:
                node_id = stack.pop()

                if node_id in seen:
                    continue

                seen.add(node_id)
                visited.append(node_id)

                # Add neighbors in reverse for correct order
                neighbors = list(self._adjacency.get(node_id, {}).keys())
                for neighbor in reversed(neighbors):
                    if neighbor not in seen:
                        stack.append(neighbor)

            return visited

    # -------------------------------------------------------------------------
    # SHORTEST PATHS
    # -------------------------------------------------------------------------

    def dijkstra(
        self,
        start: str,
        end: Optional[str] = None
    ) -> Dict[str, Tuple[float, List[str]]]:
        """
        Dijkstra's shortest path algorithm.
        Returns dict of {node: (distance, path)}.
        """
        with self._lock:
            if start not in self._nodes:
                return {}

            distances: Dict[str, float] = {start: 0}
            predecessors: Dict[str, Optional[str]] = {start: None}
            pq = [(0, start)]
            visited = set()

            while pq:
                dist, current = heapq.heappop(pq)

                if current in visited:
                    continue

                visited.add(current)

                if end and current == end:
                    break

                for neighbor, edge in self._adjacency.get(current, {}).items():
                    if neighbor in visited:
                        continue

                    new_dist = dist + edge.weight

                    if neighbor not in distances or new_dist < distances[neighbor]:
                        distances[neighbor] = new_dist
                        predecessors[neighbor] = current
                        heapq.heappush(pq, (new_dist, neighbor))

            # Build paths
            result = {}
            for node, dist in distances.items():
                path = []
                current = node
                while current is not None:
                    path.append(current)
                    current = predecessors.get(current)
                path.reverse()
                result[node] = (dist, path)

            return result

    def shortest_path(self, start: str, end: str) -> Optional[Path]:
        """Find shortest path between two nodes."""
        with self._lock:
            result = self.dijkstra(start, end)

            if end not in result:
                return None

            dist, node_ids = result[end]

            # Build path object
            path = Path(nodes=node_ids, total_weight=dist)

            # Add edges
            for i in range(len(node_ids) - 1):
                edge = self.get_edge(node_ids[i], node_ids[i + 1])
                if edge:
                    path.edges.append(edge)

            return path

    def all_paths(
        self,
        start: str,
        end: str,
        max_length: Optional[int] = None
    ) -> List[Path]:
        """Find all paths between two nodes."""
        with self._lock:
            if start not in self._nodes or end not in self._nodes:
                return []

            all_paths = []
            current_path = [start]
            visited = {start}

            def dfs(current: str) -> None:
                if current == end:
                    # Build path
                    path = Path(nodes=current_path.copy())
                    for i in range(len(current_path) - 1):
                        edge = self.get_edge(current_path[i], current_path[i + 1])
                        if edge:
                            path.edges.append(edge)
                            path.total_weight += edge.weight
                    all_paths.append(path)
                    return

                if max_length and len(current_path) >= max_length:
                    return

                for neighbor in self._adjacency.get(current, {}):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        current_path.append(neighbor)
                        dfs(neighbor)
                        current_path.pop()
                        visited.remove(neighbor)

            dfs(start)
            return all_paths

    # -------------------------------------------------------------------------
    # TOPOLOGICAL SORT
    # -------------------------------------------------------------------------

    def topological_sort(self) -> Optional[List[str]]:
        """
        Topological sort (Kahn's algorithm).
        Returns None if graph has cycles.
        """
        with self._lock:
            if self.graph_type == GraphType.UNDIRECTED:
                return None

            # Calculate in-degrees
            in_degree = defaultdict(int)
            for node in self._nodes:
                in_degree[node] = len(self._reverse_adjacency.get(node, {}))

            # Start with nodes with no incoming edges
            queue = deque([n for n in self._nodes if in_degree[n] == 0])
            result = []

            while queue:
                node = queue.popleft()
                result.append(node)

                for neighbor in self._adjacency.get(node, {}):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

            # Check for cycle
            if len(result) != len(self._nodes):
                return None

            return result

    # -------------------------------------------------------------------------
    # CONNECTED COMPONENTS
    # -------------------------------------------------------------------------

    def connected_components(self) -> List[Set[str]]:
        """Find connected components."""
        with self._lock:
            components = []
            visited = set()

            for start_node in self._nodes:
                if start_node in visited:
                    continue

                component = set()
                queue = deque([start_node])

                while queue:
                    node = queue.popleft()
                    if node in visited:
                        continue

                    visited.add(node)
                    component.add(node)

                    # Add all connected nodes
                    queue.extend(self._adjacency.get(node, {}).keys())

                    if self.graph_type != GraphType.UNDIRECTED:
                        queue.extend(self._reverse_adjacency.get(node, {}).keys())

                if component:
                    components.append(component)

            return components

    def is_connected(self) -> bool:
        """Check if graph is connected."""
        with self._lock:
            if not self._nodes:
                return True

            components = self.connected_components()
            return len(components) == 1

    def strongly_connected_components(self) -> List[Set[str]]:
        """
        Find strongly connected components (Kosaraju's algorithm).
        Only for directed graphs.
        """
        with self._lock:
            if self.graph_type == GraphType.UNDIRECTED:
                return self.connected_components()

            # First DFS to get finish order
            visited = set()
            finish_order = []

            def dfs1(node: str) -> None:
                visited.add(node)
                for neighbor in self._adjacency.get(node, {}):
                    if neighbor not in visited:
                        dfs1(neighbor)
                finish_order.append(node)

            for node in self._nodes:
                if node not in visited:
                    dfs1(node)

            # Second DFS on reverse graph
            visited.clear()
            components = []

            def dfs2(node: str, component: Set[str]) -> None:
                visited.add(node)
                component.add(node)
                for neighbor in self._reverse_adjacency.get(node, {}):
                    if neighbor not in visited:
                        dfs2(neighbor, component)

            for node in reversed(finish_order):
                if node not in visited:
                    component: Set[str] = set()
                    dfs2(node, component)
                    components.append(component)

            return components

    # -------------------------------------------------------------------------
    # SUBGRAPH
    # -------------------------------------------------------------------------

    def subgraph(self, node_ids: Set[str]) -> 'Graph[T]':
        """Extract subgraph containing specified nodes."""
        with self._lock:
            sub = Graph(self.graph_type)

            for node_id in node_ids:
                if node_id in self._nodes:
                    node = self._nodes[node_id]
                    sub.add_node(node_id, node.data, **node.metadata)

            for node_id in node_ids:
                for target, edge in self._adjacency.get(node_id, {}).items():
                    if target in node_ids:
                        sub.add_edge(
                            node_id, target,
                            weight=edge.weight,
                            label=edge.label,
                            **edge.metadata
                        )

            return sub

    # -------------------------------------------------------------------------
    # STATS
    # -------------------------------------------------------------------------

    def get_stats(self) -> GraphStats:
        """Get graph statistics."""
        with self._lock:
            n = len(self._nodes)
            e = self.edge_count()

            max_edges = n * (n - 1)
            if self.graph_type == GraphType.UNDIRECTED:
                max_edges //= 2

            density = e / max_edges if max_edges > 0 else 0

            return GraphStats(
                node_count=n,
                edge_count=e,
                density=density,
                is_connected=self.is_connected(),
                has_cycles=self.has_cycle(),
                components=len(self.connected_components())
            )

    # -------------------------------------------------------------------------
    # SERIALIZATION
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph to dictionary."""
        with self._lock:
            return {
                "graph_id": self.graph_id,
                "graph_type": self.graph_type.value,
                "nodes": [
                    {
                        "node_id": n.node_id,
                        "data": n.data,
                        "metadata": n.metadata
                    }
                    for n in self._nodes.values()
                ],
                "edges": [
                    {
                        "source": e.source,
                        "target": e.target,
                        "weight": e.weight,
                        "label": e.label,
                        "metadata": e.metadata
                    }
                    for e in self.get_edges()
                ]
            }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Graph':
        """Deserialize graph from dictionary."""
        graph_type = GraphType(data.get("graph_type", "directed"))
        graph = cls(graph_type)
        graph.graph_id = data.get("graph_id", str(uuid.uuid4()))

        for node_data in data.get("nodes", []):
            graph.add_node(
                node_data["node_id"],
                node_data.get("data"),
                **node_data.get("metadata", {})
            )

        for edge_data in data.get("edges", []):
            graph.add_edge(
                edge_data["source"],
                edge_data["target"],
                weight=edge_data.get("weight", 1.0),
                label=edge_data.get("label"),
                **edge_data.get("metadata", {})
            )

        return graph


# =============================================================================
# GRAPH MANAGER
# =============================================================================

class GraphManager:
    """
    Graph Manager for BAEL.

    Manages multiple graphs.
    """

    def __init__(self):
        self._graphs: Dict[str, Graph] = {}
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # GRAPH MANAGEMENT
    # -------------------------------------------------------------------------

    def create_graph(
        self,
        graph_type: GraphType = GraphType.DIRECTED,
        graph_id: Optional[str] = None
    ) -> Graph:
        """Create a new graph."""
        graph = Graph(graph_type)
        if graph_id:
            graph.graph_id = graph_id

        with self._lock:
            self._graphs[graph.graph_id] = graph

        return graph

    def get_graph(self, graph_id: str) -> Optional[Graph]:
        """Get graph by ID."""
        with self._lock:
            return self._graphs.get(graph_id)

    def delete_graph(self, graph_id: str) -> bool:
        """Delete a graph."""
        with self._lock:
            if graph_id in self._graphs:
                del self._graphs[graph_id]
                return True
            return False

    def list_graphs(self) -> List[Dict[str, Any]]:
        """List all graphs."""
        with self._lock:
            return [
                {
                    "graph_id": g.graph_id,
                    "type": g.graph_type.value,
                    "nodes": g.node_count(),
                    "edges": g.edge_count()
                }
                for g in self._graphs.values()
            ]

    # -------------------------------------------------------------------------
    # GRAPH ALGORITHMS
    # -------------------------------------------------------------------------

    def find_path(
        self,
        graph_id: str,
        start: str,
        end: str
    ) -> Optional[Path]:
        """Find shortest path in graph."""
        graph = self.get_graph(graph_id)
        if not graph:
            return None
        return graph.shortest_path(start, end)

    def topological_order(self, graph_id: str) -> Optional[List[str]]:
        """Get topological order of graph."""
        graph = self.get_graph(graph_id)
        if not graph:
            return None
        return graph.topological_sort()

    def find_components(self, graph_id: str) -> List[Set[str]]:
        """Find connected components."""
        graph = self.get_graph(graph_id)
        if not graph:
            return []
        return graph.connected_components()

    # -------------------------------------------------------------------------
    # GRAPH OPERATIONS
    # -------------------------------------------------------------------------

    def merge_graphs(
        self,
        graph_ids: List[str],
        graph_type: GraphType = GraphType.DIRECTED
    ) -> Optional[Graph]:
        """Merge multiple graphs."""
        merged = self.create_graph(graph_type)

        with self._lock:
            for gid in graph_ids:
                source = self._graphs.get(gid)
                if not source:
                    continue

                for node in source.get_nodes():
                    if not merged.has_node(node.node_id):
                        merged.add_node(
                            node.node_id,
                            node.data,
                            **node.metadata
                        )

                for edge in source.get_edges():
                    if not merged.has_edge(edge.source, edge.target):
                        merged.add_edge(
                            edge.source,
                            edge.target,
                            weight=edge.weight,
                            label=edge.label,
                            **edge.metadata
                        )

        return merged

    def clone_graph(self, graph_id: str) -> Optional[Graph]:
        """Clone a graph."""
        with self._lock:
            source = self._graphs.get(graph_id)
            if not source:
                return None

            data = source.to_dict()
            data["graph_id"] = str(uuid.uuid4())
            cloned = Graph.from_dict(data)
            self._graphs[cloned.graph_id] = cloned

            return cloned


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Graph Manager."""
    print("=" * 70)
    print("BAEL - GRAPH MANAGER DEMO")
    print("Advanced Graph Operations for AI Agents")
    print("=" * 70)
    print()

    manager = GraphManager()

    # 1. Create Directed Graph
    print("1. DIRECTED GRAPH:")
    print("-" * 40)

    graph = manager.create_graph(GraphType.DIRECTED)

    graph.add_node("A", data="Start")
    graph.add_node("B", data="Process 1")
    graph.add_node("C", data="Process 2")
    graph.add_node("D", data="End")

    graph.add_edge("A", "B", weight=1.0)
    graph.add_edge("A", "C", weight=2.0)
    graph.add_edge("B", "D", weight=1.0)
    graph.add_edge("C", "D", weight=1.0)

    print(f"   Nodes: {[n.node_id for n in graph.get_nodes()]}")
    print(f"   Edges: {[(e.source, e.target) for e in graph.get_edges()]}")
    print()

    # 2. Graph Statistics
    print("2. GRAPH STATISTICS:")
    print("-" * 40)

    stats = graph.get_stats()
    print(f"   Nodes: {stats.node_count}")
    print(f"   Edges: {stats.edge_count}")
    print(f"   Density: {stats.density:.2f}")
    print(f"   Connected: {stats.is_connected}")
    print(f"   Has cycles: {stats.has_cycles}")
    print()

    # 3. BFS Traversal
    print("3. BFS TRAVERSAL:")
    print("-" * 40)

    result = graph.bfs("A")
    print(f"   Visited order: {result.visited}")
    print(f"   Discovery times: {result.discovery_time}")
    print()

    # 4. DFS Traversal
    print("4. DFS TRAVERSAL:")
    print("-" * 40)

    result = graph.dfs("A")
    print(f"   Visited order: {result.visited}")
    print(f"   Finish times: {result.finish_time}")
    print()

    # 5. Shortest Path
    print("5. SHORTEST PATH:")
    print("-" * 40)

    path = graph.shortest_path("A", "D")
    if path:
        print(f"   Path A -> D: {path.nodes}")
        print(f"   Total weight: {path.total_weight}")
    print()

    # 6. All Paths
    print("6. ALL PATHS:")
    print("-" * 40)

    paths = graph.all_paths("A", "D")
    for i, p in enumerate(paths):
        print(f"   Path {i + 1}: {p.nodes} (weight: {p.total_weight})")
    print()

    # 7. Topological Sort
    print("7. TOPOLOGICAL SORT:")
    print("-" * 40)

    topo = graph.topological_sort()
    print(f"   Topological order: {topo}")
    print()

    # 8. Graph with Cycle
    print("8. CYCLE DETECTION:")
    print("-" * 40)

    cyclic = manager.create_graph(GraphType.DIRECTED)
    cyclic.add_edge("X", "Y")
    cyclic.add_edge("Y", "Z")
    cyclic.add_edge("Z", "X")  # Creates cycle

    print(f"   Has cycle: {cyclic.has_cycle()}")
    cycles = cyclic.find_cycles()
    if cycles:
        print(f"   Cycle found: {cycles[0]}")
    print()

    # 9. DAG (No Cycles Allowed)
    print("9. DAG (DIRECTED ACYCLIC GRAPH):")
    print("-" * 40)

    dag = manager.create_graph(GraphType.DAG)
    dag.add_edge("1", "2")
    dag.add_edge("1", "3")
    dag.add_edge("2", "4")
    dag.add_edge("3", "4")

    # Try to add edge that would create cycle
    result = dag.add_edge("4", "1")
    print(f"   Edge 4->1 added: {result is not None}")
    print(f"   DAG nodes: {[n.node_id for n in dag.get_nodes()]}")
    print(f"   Topological: {dag.topological_sort()}")
    print()

    # 10. Undirected Graph
    print("10. UNDIRECTED GRAPH:")
    print("-" * 40)

    undirected = manager.create_graph(GraphType.UNDIRECTED)
    undirected.add_edge("P", "Q")
    undirected.add_edge("Q", "R")

    print(f"   P neighbors: {undirected.get_neighbors('P')}")
    print(f"   R neighbors: {undirected.get_neighbors('R')}")
    print()

    # 11. Connected Components
    print("11. CONNECTED COMPONENTS:")
    print("-" * 40)

    disconnected = manager.create_graph(GraphType.UNDIRECTED)
    disconnected.add_edge("A1", "A2")
    disconnected.add_edge("A2", "A3")
    disconnected.add_edge("B1", "B2")  # Separate component

    components = disconnected.connected_components()
    print(f"   Components: {[list(c) for c in components]}")
    print(f"   Is connected: {disconnected.is_connected()}")
    print()

    # 12. Strongly Connected Components
    print("12. STRONGLY CONNECTED COMPONENTS:")
    print("-" * 40)

    scc_graph = manager.create_graph(GraphType.DIRECTED)
    # Component 1: A <-> B
    scc_graph.add_edge("A", "B")
    scc_graph.add_edge("B", "A")
    # Component 2: C <-> D
    scc_graph.add_edge("C", "D")
    scc_graph.add_edge("D", "C")
    # Link between components
    scc_graph.add_edge("B", "C")

    sccs = scc_graph.strongly_connected_components()
    print(f"   SCCs: {[list(s) for s in sccs]}")
    print()

    # 13. Subgraph Extraction
    print("13. SUBGRAPH EXTRACTION:")
    print("-" * 40)

    subgraph = graph.subgraph({"A", "B", "D"})
    print(f"   Original nodes: {[n.node_id for n in graph.get_nodes()]}")
    print(f"   Subgraph nodes: {[n.node_id for n in subgraph.get_nodes()]}")
    print(f"   Subgraph edges: {[(e.source, e.target) for e in subgraph.get_edges()]}")
    print()

    # 14. Dijkstra's Algorithm
    print("14. DIJKSTRA'S ALGORITHM:")
    print("-" * 40)

    weighted = manager.create_graph(GraphType.DIRECTED)
    weighted.add_edge("S", "A", weight=4)
    weighted.add_edge("S", "B", weight=2)
    weighted.add_edge("A", "C", weight=5)
    weighted.add_edge("B", "A", weight=1)
    weighted.add_edge("B", "C", weight=8)
    weighted.add_edge("C", "D", weight=3)
    weighted.add_edge("A", "D", weight=10)

    distances = weighted.dijkstra("S")
    for node, (dist, path) in sorted(distances.items()):
        print(f"   S -> {node}: distance={dist}, path={path}")
    print()

    # 15. Graph Serialization
    print("15. GRAPH SERIALIZATION:")
    print("-" * 40)

    data = graph.to_dict()
    print(f"   Serialized nodes: {len(data['nodes'])}")
    print(f"   Serialized edges: {len(data['edges'])}")

    restored = Graph.from_dict(data)
    print(f"   Restored nodes: {restored.node_count()}")
    print(f"   Restored edges: {restored.edge_count()}")
    print()

    # 16. Clone Graph
    print("16. CLONE GRAPH:")
    print("-" * 40)

    cloned = manager.clone_graph(graph.graph_id)
    if cloned:
        print(f"   Original ID: {graph.graph_id}")
        print(f"   Cloned ID: {cloned.graph_id}")
        print(f"   Nodes match: {cloned.node_count() == graph.node_count()}")
    print()

    # 17. Merge Graphs
    print("17. MERGE GRAPHS:")
    print("-" * 40)

    g1 = manager.create_graph()
    g1.add_edge("X", "Y")
    g2 = manager.create_graph()
    g2.add_edge("Y", "Z")

    merged = manager.merge_graphs([g1.graph_id, g2.graph_id])
    if merged:
        print(f"   Merged nodes: {[n.node_id for n in merged.get_nodes()]}")
        print(f"   Merged edges: {[(e.source, e.target) for e in merged.get_edges()]}")
    print()

    # 18. List All Graphs
    print("18. LIST ALL GRAPHS:")
    print("-" * 40)

    graphs = manager.list_graphs()
    print(f"   Total graphs: {len(graphs)}")
    for g in graphs[:3]:
        print(f"   - {g['graph_id'][:8]}...: {g['nodes']} nodes, {g['edges']} edges")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Graph Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
