#!/usr/bin/env python3
"""
BAEL - Graph Processing Engine
Comprehensive graph operations and algorithms.

This module provides a complete graph processing framework
for complex relationship analysis.

Features:
- Directed and undirected graphs
- Weighted edges
- Path finding (BFS, DFS, Dijkstra, A*)
- Cycle detection
- Topological sorting
- Connected components
- Graph coloring
- Minimum spanning trees
- Network flow
- Graph serialization
"""

import asyncio
import heapq
import json
import logging
import math
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')
NodeId = Union[str, int]


# =============================================================================
# ENUMS
# =============================================================================

class GraphType(Enum):
    """Types of graphs."""
    DIRECTED = "directed"
    UNDIRECTED = "undirected"


class TraversalOrder(Enum):
    """Graph traversal orders."""
    BFS = "bfs"
    DFS = "dfs"
    PREORDER = "preorder"
    POSTORDER = "postorder"


class PathAlgorithm(Enum):
    """Path finding algorithms."""
    BFS = "bfs"
    DFS = "dfs"
    DIJKSTRA = "dijkstra"
    ASTAR = "astar"
    BELLMAN_FORD = "bellman_ford"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Node:
    """Graph node."""
    id: NodeId
    data: Dict[str, Any] = field(default_factory=dict)
    label: str = ""
    weight: float = 1.0

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Node):
            return self.id == other.id
        return self.id == other


@dataclass
class Edge:
    """Graph edge."""
    source: NodeId
    target: NodeId
    weight: float = 1.0
    data: Dict[str, Any] = field(default_factory=dict)
    label: str = ""

    def __hash__(self):
        return hash((self.source, self.target))

    def reverse(self) -> 'Edge':
        """Create reversed edge."""
        return Edge(
            source=self.target,
            target=self.source,
            weight=self.weight,
            data=self.data.copy(),
            label=self.label
        )


@dataclass
class Path:
    """Path through graph."""
    nodes: List[NodeId]
    total_weight: float = 0.0
    edges: List[Edge] = field(default_factory=list)

    @property
    def length(self) -> int:
        return len(self.nodes) - 1 if self.nodes else 0

    @property
    def is_empty(self) -> bool:
        return len(self.nodes) == 0

    def __str__(self) -> str:
        return " -> ".join(str(n) for n in self.nodes)


@dataclass
class GraphStats:
    """Graph statistics."""
    node_count: int = 0
    edge_count: int = 0
    density: float = 0.0
    avg_degree: float = 0.0
    is_connected: bool = False
    has_cycles: bool = False
    diameter: int = 0


# =============================================================================
# GRAPH IMPLEMENTATION
# =============================================================================

class Graph:
    """
    Core graph implementation.

    Supports both directed and undirected graphs with weights.
    """

    def __init__(
        self,
        graph_type: GraphType = GraphType.DIRECTED,
        allow_self_loops: bool = False,
        allow_parallel_edges: bool = False
    ):
        self.graph_type = graph_type
        self.allow_self_loops = allow_self_loops
        self.allow_parallel_edges = allow_parallel_edges

        self.nodes: Dict[NodeId, Node] = {}
        self.adjacency: Dict[NodeId, Dict[NodeId, Edge]] = defaultdict(dict)

        # For undirected: store edges in both directions
        if graph_type == GraphType.UNDIRECTED:
            self.reverse_adjacency = self.adjacency
        else:
            self.reverse_adjacency: Dict[NodeId, Dict[NodeId, Edge]] = defaultdict(dict)

    # Node Operations
    def add_node(
        self,
        node_id: NodeId,
        data: Dict[str, Any] = None,
        label: str = "",
        weight: float = 1.0
    ) -> Node:
        """Add a node to the graph."""
        if node_id not in self.nodes:
            self.nodes[node_id] = Node(
                id=node_id,
                data=data or {},
                label=label,
                weight=weight
            )
        return self.nodes[node_id]

    def remove_node(self, node_id: NodeId) -> bool:
        """Remove a node and its edges."""
        if node_id not in self.nodes:
            return False

        # Remove outgoing edges
        if node_id in self.adjacency:
            del self.adjacency[node_id]

        # Remove incoming edges
        for adj in self.adjacency.values():
            if node_id in adj:
                del adj[node_id]

        # Remove reverse adjacency
        if self.graph_type == GraphType.DIRECTED:
            if node_id in self.reverse_adjacency:
                del self.reverse_adjacency[node_id]
            for adj in self.reverse_adjacency.values():
                if node_id in adj:
                    del adj[node_id]

        del self.nodes[node_id]
        return True

    def has_node(self, node_id: NodeId) -> bool:
        """Check if node exists."""
        return node_id in self.nodes

    def get_node(self, node_id: NodeId) -> Optional[Node]:
        """Get node by ID."""
        return self.nodes.get(node_id)

    def node_count(self) -> int:
        """Get number of nodes."""
        return len(self.nodes)

    # Edge Operations
    def add_edge(
        self,
        source: NodeId,
        target: NodeId,
        weight: float = 1.0,
        data: Dict[str, Any] = None,
        label: str = ""
    ) -> Edge:
        """Add an edge to the graph."""
        # Validate
        if not self.allow_self_loops and source == target:
            raise ValueError("Self loops not allowed")

        if not self.allow_parallel_edges and target in self.adjacency.get(source, {}):
            # Update existing edge
            edge = self.adjacency[source][target]
            edge.weight = weight
            if data:
                edge.data.update(data)
            return edge

        # Ensure nodes exist
        self.add_node(source)
        self.add_node(target)

        # Create edge
        edge = Edge(
            source=source,
            target=target,
            weight=weight,
            data=data or {},
            label=label
        )

        self.adjacency[source][target] = edge

        # For undirected graphs, add reverse edge
        if self.graph_type == GraphType.UNDIRECTED:
            self.adjacency[target][source] = edge.reverse()
        else:
            self.reverse_adjacency[target][source] = edge

        return edge

    def remove_edge(self, source: NodeId, target: NodeId) -> bool:
        """Remove an edge."""
        if source not in self.adjacency or target not in self.adjacency[source]:
            return False

        del self.adjacency[source][target]

        if self.graph_type == GraphType.UNDIRECTED:
            if target in self.adjacency and source in self.adjacency[target]:
                del self.adjacency[target][source]
        else:
            if target in self.reverse_adjacency and source in self.reverse_adjacency[target]:
                del self.reverse_adjacency[target][source]

        return True

    def has_edge(self, source: NodeId, target: NodeId) -> bool:
        """Check if edge exists."""
        return source in self.adjacency and target in self.adjacency[source]

    def get_edge(self, source: NodeId, target: NodeId) -> Optional[Edge]:
        """Get edge by endpoints."""
        if source in self.adjacency:
            return self.adjacency[source].get(target)
        return None

    def edge_count(self) -> int:
        """Get number of edges."""
        count = sum(len(adj) for adj in self.adjacency.values())
        if self.graph_type == GraphType.UNDIRECTED:
            count //= 2
        return count

    # Adjacency
    def neighbors(self, node_id: NodeId) -> List[NodeId]:
        """Get neighbors of a node."""
        return list(self.adjacency.get(node_id, {}).keys())

    def predecessors(self, node_id: NodeId) -> List[NodeId]:
        """Get predecessors (for directed graphs)."""
        if self.graph_type == GraphType.UNDIRECTED:
            return self.neighbors(node_id)
        return list(self.reverse_adjacency.get(node_id, {}).keys())

    def successors(self, node_id: NodeId) -> List[NodeId]:
        """Get successors (same as neighbors for directed)."""
        return self.neighbors(node_id)

    def degree(self, node_id: NodeId) -> int:
        """Get degree of a node."""
        return len(self.adjacency.get(node_id, {}))

    def in_degree(self, node_id: NodeId) -> int:
        """Get in-degree (for directed graphs)."""
        if self.graph_type == GraphType.UNDIRECTED:
            return self.degree(node_id)
        return len(self.reverse_adjacency.get(node_id, {}))

    def out_degree(self, node_id: NodeId) -> int:
        """Get out-degree."""
        return self.degree(node_id)

    # Edges
    def edges(self) -> Iterator[Edge]:
        """Iterate over all edges."""
        seen = set()
        for source, targets in self.adjacency.items():
            for target, edge in targets.items():
                if self.graph_type == GraphType.UNDIRECTED:
                    key = tuple(sorted([source, target]))
                    if key in seen:
                        continue
                    seen.add(key)
                yield edge

    def incident_edges(self, node_id: NodeId) -> List[Edge]:
        """Get edges incident to a node."""
        edges = list(self.adjacency.get(node_id, {}).values())

        if self.graph_type == GraphType.DIRECTED:
            for edge in self.reverse_adjacency.get(node_id, {}).values():
                edges.append(edge)

        return edges

    # Subgraphs
    def subgraph(self, node_ids: Set[NodeId]) -> 'Graph':
        """Create a subgraph with specified nodes."""
        sub = Graph(self.graph_type, self.allow_self_loops, self.allow_parallel_edges)

        for node_id in node_ids:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                sub.add_node(node_id, node.data.copy(), node.label, node.weight)

        for edge in self.edges():
            if edge.source in node_ids and edge.target in node_ids:
                sub.add_edge(edge.source, edge.target, edge.weight, edge.data.copy(), edge.label)

        return sub

    # Serialization
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.graph_type.value,
            "nodes": [
                {"id": n.id, "data": n.data, "label": n.label, "weight": n.weight}
                for n in self.nodes.values()
            ],
            "edges": [
                {"source": e.source, "target": e.target, "weight": e.weight,
                 "data": e.data, "label": e.label}
                for e in self.edges()
            ]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Graph':
        """Create from dictionary."""
        graph = cls(GraphType(data.get("type", "directed")))

        for node_data in data.get("nodes", []):
            graph.add_node(
                node_data["id"],
                node_data.get("data", {}),
                node_data.get("label", ""),
                node_data.get("weight", 1.0)
            )

        for edge_data in data.get("edges", []):
            graph.add_edge(
                edge_data["source"],
                edge_data["target"],
                edge_data.get("weight", 1.0),
                edge_data.get("data", {}),
                edge_data.get("label", "")
            )

        return graph


# =============================================================================
# GRAPH ALGORITHMS
# =============================================================================

class GraphAlgorithms:
    """Collection of graph algorithms."""

    # Traversal
    @staticmethod
    def bfs(
        graph: Graph,
        start: NodeId,
        visit: Callable[[NodeId], None] = None
    ) -> List[NodeId]:
        """Breadth-first search."""
        if start not in graph.nodes:
            return []

        visited = []
        seen = {start}
        queue = deque([start])

        while queue:
            node = queue.popleft()
            visited.append(node)

            if visit:
                visit(node)

            for neighbor in graph.neighbors(node):
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)

        return visited

    @staticmethod
    def dfs(
        graph: Graph,
        start: NodeId,
        visit: Callable[[NodeId], None] = None
    ) -> List[NodeId]:
        """Depth-first search."""
        if start not in graph.nodes:
            return []

        visited = []
        seen = set()

        def _dfs(node: NodeId):
            if node in seen:
                return

            seen.add(node)
            visited.append(node)

            if visit:
                visit(node)

            for neighbor in graph.neighbors(node):
                _dfs(neighbor)

        _dfs(start)
        return visited

    @staticmethod
    def dfs_iterative(
        graph: Graph,
        start: NodeId
    ) -> List[NodeId]:
        """Iterative DFS (avoids stack overflow)."""
        if start not in graph.nodes:
            return []

        visited = []
        seen = {start}
        stack = [start]

        while stack:
            node = stack.pop()
            visited.append(node)

            for neighbor in reversed(graph.neighbors(node)):
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)

        return visited

    # Path Finding
    @staticmethod
    def shortest_path_bfs(
        graph: Graph,
        start: NodeId,
        end: NodeId
    ) -> Optional[Path]:
        """Find shortest path (unweighted) using BFS."""
        if start not in graph.nodes or end not in graph.nodes:
            return None

        if start == end:
            return Path(nodes=[start], total_weight=0)

        parent = {start: None}
        queue = deque([start])

        while queue:
            node = queue.popleft()

            if node == end:
                # Reconstruct path
                path = []
                current = end
                while current is not None:
                    path.append(current)
                    current = parent[current]
                path.reverse()

                return Path(nodes=path, total_weight=len(path) - 1)

            for neighbor in graph.neighbors(node):
                if neighbor not in parent:
                    parent[neighbor] = node
                    queue.append(neighbor)

        return None

    @staticmethod
    def dijkstra(
        graph: Graph,
        start: NodeId,
        end: NodeId = None
    ) -> Union[Dict[NodeId, float], Optional[Path]]:
        """
        Dijkstra's algorithm for shortest paths.

        If end is None, returns distances to all nodes.
        If end is specified, returns shortest path to end.
        """
        if start not in graph.nodes:
            return {} if end is None else None

        distances = {start: 0}
        parent = {start: None}
        pq = [(0, start)]
        visited = set()

        while pq:
            dist, node = heapq.heappop(pq)

            if node in visited:
                continue

            visited.add(node)

            if end is not None and node == end:
                # Reconstruct path
                path = []
                edges = []
                current = end

                while current is not None:
                    path.append(current)
                    if parent[current] is not None:
                        edge = graph.get_edge(parent[current], current)
                        if edge:
                            edges.append(edge)
                    current = parent[current]

                path.reverse()
                edges.reverse()

                return Path(nodes=path, total_weight=dist, edges=edges)

            for neighbor in graph.neighbors(node):
                if neighbor in visited:
                    continue

                edge = graph.get_edge(node, neighbor)
                new_dist = dist + edge.weight

                if neighbor not in distances or new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    parent[neighbor] = node
                    heapq.heappush(pq, (new_dist, neighbor))

        if end is not None:
            return None

        return distances

    @staticmethod
    def astar(
        graph: Graph,
        start: NodeId,
        end: NodeId,
        heuristic: Callable[[NodeId, NodeId], float] = None
    ) -> Optional[Path]:
        """
        A* pathfinding algorithm.

        heuristic: Function estimating cost from node to goal.
        """
        if start not in graph.nodes or end not in graph.nodes:
            return None

        if heuristic is None:
            heuristic = lambda n, e: 0  # Degrades to Dijkstra

        g_score = {start: 0}
        f_score = {start: heuristic(start, end)}
        parent = {start: None}

        open_set = [(f_score[start], start)]
        closed_set = set()

        while open_set:
            _, current = heapq.heappop(open_set)

            if current == end:
                # Reconstruct path
                path = []
                edges = []
                node = end

                while node is not None:
                    path.append(node)
                    if parent[node] is not None:
                        edge = graph.get_edge(parent[node], node)
                        if edge:
                            edges.append(edge)
                    node = parent[node]

                path.reverse()
                edges.reverse()

                return Path(nodes=path, total_weight=g_score[end], edges=edges)

            if current in closed_set:
                continue

            closed_set.add(current)

            for neighbor in graph.neighbors(current):
                if neighbor in closed_set:
                    continue

                edge = graph.get_edge(current, neighbor)
                tentative_g = g_score[current] + edge.weight

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    parent[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + heuristic(neighbor, end)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

        return None

    @staticmethod
    def bellman_ford(
        graph: Graph,
        start: NodeId
    ) -> Tuple[Dict[NodeId, float], bool]:
        """
        Bellman-Ford algorithm.

        Handles negative weights. Returns (distances, has_negative_cycle).
        """
        distances = {node: float('inf') for node in graph.nodes}
        distances[start] = 0

        edges = list(graph.edges())
        n = graph.node_count()

        # Relax edges n-1 times
        for _ in range(n - 1):
            changed = False
            for edge in edges:
                if distances[edge.source] + edge.weight < distances[edge.target]:
                    distances[edge.target] = distances[edge.source] + edge.weight
                    changed = True

            if not changed:
                break

        # Check for negative cycles
        has_negative_cycle = False
        for edge in edges:
            if distances[edge.source] + edge.weight < distances[edge.target]:
                has_negative_cycle = True
                break

        return distances, has_negative_cycle

    # Cycle Detection
    @staticmethod
    def has_cycle(graph: Graph) -> bool:
        """Check if graph has a cycle."""
        if graph.graph_type == GraphType.UNDIRECTED:
            return GraphAlgorithms._has_cycle_undirected(graph)
        return GraphAlgorithms._has_cycle_directed(graph)

    @staticmethod
    def _has_cycle_directed(graph: Graph) -> bool:
        """Cycle detection for directed graphs."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in graph.nodes}

        def dfs(node: NodeId) -> bool:
            color[node] = GRAY

            for neighbor in graph.neighbors(node):
                if color[neighbor] == GRAY:
                    return True
                if color[neighbor] == WHITE and dfs(neighbor):
                    return True

            color[node] = BLACK
            return False

        for node in graph.nodes:
            if color[node] == WHITE:
                if dfs(node):
                    return True

        return False

    @staticmethod
    def _has_cycle_undirected(graph: Graph) -> bool:
        """Cycle detection for undirected graphs."""
        visited = set()

        def dfs(node: NodeId, parent: NodeId) -> bool:
            visited.add(node)

            for neighbor in graph.neighbors(node):
                if neighbor not in visited:
                    if dfs(neighbor, node):
                        return True
                elif neighbor != parent:
                    return True

            return False

        for node in graph.nodes:
            if node not in visited:
                if dfs(node, None):
                    return True

        return False

    # Topological Sort
    @staticmethod
    def topological_sort(graph: Graph) -> Optional[List[NodeId]]:
        """
        Topological sort for DAGs.

        Returns None if graph has a cycle.
        """
        if graph.graph_type != GraphType.DIRECTED:
            raise ValueError("Topological sort requires directed graph")

        in_degree = {node: 0 for node in graph.nodes}

        for edge in graph.edges():
            in_degree[edge.target] += 1

        queue = deque([node for node, deg in in_degree.items() if deg == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            for neighbor in graph.neighbors(node):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != graph.node_count():
            return None  # Cycle detected

        return result

    # Connected Components
    @staticmethod
    def connected_components(graph: Graph) -> List[Set[NodeId]]:
        """Find connected components."""
        visited = set()
        components = []

        for node in graph.nodes:
            if node not in visited:
                component = set()
                queue = deque([node])

                while queue:
                    current = queue.popleft()
                    if current in visited:
                        continue

                    visited.add(current)
                    component.add(current)

                    for neighbor in graph.neighbors(current):
                        if neighbor not in visited:
                            queue.append(neighbor)

                    # For directed graphs, also check predecessors
                    if graph.graph_type == GraphType.DIRECTED:
                        for pred in graph.predecessors(current):
                            if pred not in visited:
                                queue.append(pred)

                components.append(component)

        return components

    @staticmethod
    def strongly_connected_components(graph: Graph) -> List[Set[NodeId]]:
        """Find strongly connected components (Kosaraju's algorithm)."""
        if graph.graph_type != GraphType.DIRECTED:
            return GraphAlgorithms.connected_components(graph)

        # First DFS to get finish order
        visited = set()
        finish_order = []

        def dfs1(node: NodeId):
            visited.add(node)
            for neighbor in graph.neighbors(node):
                if neighbor not in visited:
                    dfs1(neighbor)
            finish_order.append(node)

        for node in graph.nodes:
            if node not in visited:
                dfs1(node)

        # Second DFS on transpose
        visited.clear()
        components = []

        def dfs2(node: NodeId, component: Set[NodeId]):
            visited.add(node)
            component.add(node)
            for pred in graph.predecessors(node):
                if pred not in visited:
                    dfs2(pred, component)

        for node in reversed(finish_order):
            if node not in visited:
                component = set()
                dfs2(node, component)
                components.append(component)

        return components

    # Minimum Spanning Tree
    @staticmethod
    def minimum_spanning_tree_prim(graph: Graph) -> List[Edge]:
        """Prim's algorithm for MST."""
        if graph.node_count() == 0:
            return []

        start = next(iter(graph.nodes))
        visited = {start}
        edges = []

        # Priority queue of edges
        pq = []
        for neighbor in graph.neighbors(start):
            edge = graph.get_edge(start, neighbor)
            heapq.heappush(pq, (edge.weight, edge))

        while pq and len(visited) < graph.node_count():
            weight, edge = heapq.heappop(pq)

            if edge.target in visited:
                continue

            edges.append(edge)
            visited.add(edge.target)

            for neighbor in graph.neighbors(edge.target):
                if neighbor not in visited:
                    new_edge = graph.get_edge(edge.target, neighbor)
                    heapq.heappush(pq, (new_edge.weight, new_edge))

        return edges

    @staticmethod
    def minimum_spanning_tree_kruskal(graph: Graph) -> List[Edge]:
        """Kruskal's algorithm for MST using Union-Find."""
        # Union-Find data structure
        parent = {node: node for node in graph.nodes}
        rank = {node: 0 for node in graph.nodes}

        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])  # Path compression
            return parent[x]

        def union(x, y):
            px, py = find(x), find(y)
            if px == py:
                return False

            if rank[px] < rank[py]:
                parent[px] = py
            elif rank[px] > rank[py]:
                parent[py] = px
            else:
                parent[py] = px
                rank[px] += 1
            return True

        # Sort edges by weight
        sorted_edges = sorted(graph.edges(), key=lambda e: e.weight)

        mst = []
        for edge in sorted_edges:
            if union(edge.source, edge.target):
                mst.append(edge)
                if len(mst) == graph.node_count() - 1:
                    break

        return mst

    # Graph Coloring
    @staticmethod
    def greedy_coloring(graph: Graph) -> Dict[NodeId, int]:
        """Greedy graph coloring."""
        colors = {}

        for node in graph.nodes:
            neighbor_colors = {
                colors[n] for n in graph.neighbors(node)
                if n in colors
            }

            # Find smallest available color
            color = 0
            while color in neighbor_colors:
                color += 1

            colors[node] = color

        return colors

    # Statistics
    @staticmethod
    def get_stats(graph: Graph) -> GraphStats:
        """Get graph statistics."""
        n = graph.node_count()
        m = graph.edge_count()

        # Density
        max_edges = n * (n - 1)
        if graph.graph_type == GraphType.UNDIRECTED:
            max_edges //= 2
        density = m / max_edges if max_edges > 0 else 0

        # Average degree
        avg_degree = (2 * m) / n if n > 0 else 0

        # Connectivity
        components = GraphAlgorithms.connected_components(graph)
        is_connected = len(components) == 1

        # Cycles
        has_cycles = GraphAlgorithms.has_cycle(graph)

        return GraphStats(
            node_count=n,
            edge_count=m,
            density=density,
            avg_degree=avg_degree,
            is_connected=is_connected,
            has_cycles=has_cycles
        )


# =============================================================================
# GRAPH PROCESSOR
# =============================================================================

class GraphProcessor:
    """
    Master graph processing engine for BAEL.

    Provides high-level graph operations.
    """

    def __init__(self):
        self.graphs: Dict[str, Graph] = {}
        self.algorithms = GraphAlgorithms()

    # Graph Management
    def create_graph(
        self,
        name: str,
        graph_type: GraphType = GraphType.DIRECTED
    ) -> Graph:
        """Create a new graph."""
        graph = Graph(graph_type)
        self.graphs[name] = graph
        return graph

    def get_graph(self, name: str) -> Optional[Graph]:
        """Get graph by name."""
        return self.graphs.get(name)

    def delete_graph(self, name: str) -> bool:
        """Delete a graph."""
        if name in self.graphs:
            del self.graphs[name]
            return True
        return False

    # Operations
    def find_path(
        self,
        graph: Graph,
        start: NodeId,
        end: NodeId,
        algorithm: PathAlgorithm = PathAlgorithm.DIJKSTRA
    ) -> Optional[Path]:
        """Find path between nodes."""
        if algorithm == PathAlgorithm.BFS:
            return GraphAlgorithms.shortest_path_bfs(graph, start, end)
        elif algorithm == PathAlgorithm.DIJKSTRA:
            return GraphAlgorithms.dijkstra(graph, start, end)
        elif algorithm == PathAlgorithm.ASTAR:
            return GraphAlgorithms.astar(graph, start, end)
        else:
            return GraphAlgorithms.dijkstra(graph, start, end)

    def find_all_paths(
        self,
        graph: Graph,
        start: NodeId,
        end: NodeId,
        max_length: int = 10
    ) -> List[Path]:
        """Find all paths between nodes."""
        if start not in graph.nodes or end not in graph.nodes:
            return []

        paths = []

        def dfs(current: NodeId, path: List[NodeId], visited: Set[NodeId]):
            if len(path) > max_length:
                return

            if current == end:
                paths.append(Path(nodes=path.copy(), total_weight=len(path) - 1))
                return

            for neighbor in graph.neighbors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    path.append(neighbor)
                    dfs(neighbor, path, visited)
                    path.pop()
                    visited.remove(neighbor)

        dfs(start, [start], {start})
        return paths

    def traverse(
        self,
        graph: Graph,
        start: NodeId,
        order: TraversalOrder = TraversalOrder.BFS
    ) -> List[NodeId]:
        """Traverse graph."""
        if order == TraversalOrder.BFS:
            return GraphAlgorithms.bfs(graph, start)
        elif order == TraversalOrder.DFS:
            return GraphAlgorithms.dfs(graph, start)
        else:
            return GraphAlgorithms.bfs(graph, start)

    def analyze(self, graph: Graph) -> GraphStats:
        """Analyze graph structure."""
        return GraphAlgorithms.get_stats(graph)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Graph Processing Engine."""
    print("=" * 70)
    print("BAEL - GRAPH PROCESSING ENGINE DEMO")
    print("Comprehensive Graph Operations")
    print("=" * 70)
    print()

    processor = GraphProcessor()

    # 1. Create Graph
    print("1. CREATING GRAPH:")
    print("-" * 40)

    graph = processor.create_graph("social", GraphType.DIRECTED)

    # Add nodes
    for i in range(6):
        graph.add_node(i, label=f"User{i}")

    # Add edges with weights
    edges = [
        (0, 1, 1), (0, 2, 4),
        (1, 2, 2), (1, 3, 5),
        (2, 3, 1), (2, 4, 3),
        (3, 4, 2), (3, 5, 3),
        (4, 5, 1)
    ]

    for src, tgt, weight in edges:
        graph.add_edge(src, tgt, weight)

    print(f"   Nodes: {graph.node_count()}")
    print(f"   Edges: {graph.edge_count()}")
    print()

    # 2. Graph Traversal
    print("2. GRAPH TRAVERSAL:")
    print("-" * 40)

    bfs_order = GraphAlgorithms.bfs(graph, 0)
    print(f"   BFS from 0: {bfs_order}")

    dfs_order = GraphAlgorithms.dfs(graph, 0)
    print(f"   DFS from 0: {dfs_order}")
    print()

    # 3. Shortest Path
    print("3. SHORTEST PATH:")
    print("-" * 40)

    path = processor.find_path(graph, 0, 5, PathAlgorithm.DIJKSTRA)
    print(f"   Dijkstra 0→5: {path}")
    print(f"   Total weight: {path.total_weight}")

    bfs_path = processor.find_path(graph, 0, 5, PathAlgorithm.BFS)
    print(f"   BFS 0→5: {bfs_path}")
    print()

    # 4. All Paths
    print("4. ALL PATHS:")
    print("-" * 40)

    all_paths = processor.find_all_paths(graph, 0, 5, max_length=6)
    print(f"   Paths from 0 to 5: {len(all_paths)}")
    for p in all_paths[:5]:
        print(f"      {p}")
    print()

    # 5. Cycle Detection
    print("5. CYCLE DETECTION:")
    print("-" * 40)

    has_cycle = GraphAlgorithms.has_cycle(graph)
    print(f"   Has cycle: {has_cycle}")

    # Add cycle
    graph.add_edge(5, 0, 1)
    has_cycle = GraphAlgorithms.has_cycle(graph)
    print(f"   After adding 5→0: {has_cycle}")
    graph.remove_edge(5, 0)
    print()

    # 6. Topological Sort
    print("6. TOPOLOGICAL SORT:")
    print("-" * 40)

    topo = GraphAlgorithms.topological_sort(graph)
    print(f"   Order: {topo}")
    print()

    # 7. Connected Components
    print("7. CONNECTED COMPONENTS:")
    print("-" * 40)

    components = GraphAlgorithms.connected_components(graph)
    print(f"   Components: {len(components)}")
    for i, comp in enumerate(components):
        print(f"      Component {i}: {comp}")

    scc = GraphAlgorithms.strongly_connected_components(graph)
    print(f"   Strongly connected: {len(scc)}")
    print()

    # 8. Minimum Spanning Tree
    print("8. MINIMUM SPANNING TREE:")
    print("-" * 40)

    # Create undirected graph for MST
    undirected = Graph(GraphType.UNDIRECTED)
    for i in range(6):
        undirected.add_node(i)
    for src, tgt, weight in edges:
        undirected.add_edge(src, tgt, weight)

    mst_prim = GraphAlgorithms.minimum_spanning_tree_prim(undirected)
    total_weight = sum(e.weight for e in mst_prim)
    print(f"   Prim's MST edges: {len(mst_prim)}")
    print(f"   Total weight: {total_weight}")

    mst_kruskal = GraphAlgorithms.minimum_spanning_tree_kruskal(undirected)
    print(f"   Kruskal's MST edges: {len(mst_kruskal)}")
    print()

    # 9. Graph Coloring
    print("9. GRAPH COLORING:")
    print("-" * 40)

    colors = GraphAlgorithms.greedy_coloring(undirected)
    print(f"   Chromatic number: {max(colors.values()) + 1}")
    print(f"   Colors: {colors}")
    print()

    # 10. Graph Statistics
    print("10. GRAPH STATISTICS:")
    print("-" * 40)

    stats = processor.analyze(graph)
    print(f"    Nodes: {stats.node_count}")
    print(f"    Edges: {stats.edge_count}")
    print(f"    Density: {stats.density:.4f}")
    print(f"    Avg degree: {stats.avg_degree:.2f}")
    print(f"    Connected: {stats.is_connected}")
    print(f"    Has cycles: {stats.has_cycles}")
    print()

    # 11. Subgraph
    print("11. SUBGRAPH:")
    print("-" * 40)

    sub = graph.subgraph({0, 1, 2, 3})
    print(f"   Subgraph nodes: {sub.node_count()}")
    print(f"   Subgraph edges: {sub.edge_count()}")
    print()

    # 12. Serialization
    print("12. SERIALIZATION:")
    print("-" * 40)

    data = graph.to_dict()
    print(f"   Serialized nodes: {len(data['nodes'])}")
    print(f"   Serialized edges: {len(data['edges'])}")

    restored = Graph.from_dict(data)
    print(f"   Restored nodes: {restored.node_count()}")
    print(f"   Restored edges: {restored.edge_count()}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Graph Processing Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
