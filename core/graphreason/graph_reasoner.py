#!/usr/bin/env python3
"""
BAEL - Graph Reasoner
Advanced graph-based reasoning and analysis.

Features:
- Graph construction
- Path finding (BFS, DFS, Dijkstra)
- Centrality measures
- Community detection
- Graph patterns
- Inference on graphs
"""

import asyncio
import heapq
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class NodeType(Enum):
    """Types of nodes."""
    ENTITY = "entity"
    CONCEPT = "concept"
    EVENT = "event"
    ATTRIBUTE = "attribute"


class EdgeType(Enum):
    """Types of edges."""
    DIRECTED = "directed"
    UNDIRECTED = "undirected"
    WEIGHTED = "weighted"


class CentralityType(Enum):
    """Types of centrality measures."""
    DEGREE = "degree"
    BETWEENNESS = "betweenness"
    CLOSENESS = "closeness"
    PAGERANK = "pagerank"


class PathAlgorithm(Enum):
    """Path finding algorithms."""
    BFS = "bfs"
    DFS = "dfs"
    DIJKSTRA = "dijkstra"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Node:
    """A graph node."""
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    label: str = ""
    node_type: NodeType = NodeType.ENTITY
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    """A graph edge."""
    edge_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = ""
    target: str = ""
    label: str = ""
    edge_type: EdgeType = EdgeType.DIRECTED
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Path:
    """A path in the graph."""
    nodes: List[str] = field(default_factory=list)
    edges: List[str] = field(default_factory=list)
    total_weight: float = 0.0


@dataclass
class Community:
    """A graph community."""
    community_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nodes: List[str] = field(default_factory=list)
    density: float = 0.0


@dataclass
class CentralityResult:
    """Centrality analysis result."""
    centrality_type: CentralityType = CentralityType.DEGREE
    scores: Dict[str, float] = field(default_factory=dict)


# =============================================================================
# GRAPH STORE
# =============================================================================

class GraphStore:
    """Store for graph structure."""

    def __init__(self):
        self._nodes: Dict[str, Node] = {}
        self._edges: Dict[str, Edge] = {}
        self._adjacency: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        self._reverse_adjacency: Dict[str, List[Tuple[str, str]]] = defaultdict(list)

    def add_node(
        self,
        label: str,
        node_type: NodeType = NodeType.ENTITY,
        properties: Optional[Dict[str, Any]] = None
    ) -> Node:
        """Add a node."""
        node = Node(
            label=label,
            node_type=node_type,
            properties=properties or {}
        )
        self._nodes[node.node_id] = node
        return node

    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node."""
        return self._nodes.get(node_id)

    def get_node_by_label(self, label: str) -> Optional[Node]:
        """Get a node by label."""
        for node in self._nodes.values():
            if node.label == label:
                return node
        return None

    def add_edge(
        self,
        source: str,
        target: str,
        label: str = "",
        weight: float = 1.0,
        edge_type: EdgeType = EdgeType.DIRECTED
    ) -> Edge:
        """Add an edge."""
        edge = Edge(
            source=source,
            target=target,
            label=label,
            weight=weight,
            edge_type=edge_type
        )
        self._edges[edge.edge_id] = edge

        self._adjacency[source].append((target, edge.edge_id))
        self._reverse_adjacency[target].append((source, edge.edge_id))

        if edge_type == EdgeType.UNDIRECTED:
            self._adjacency[target].append((source, edge.edge_id))
            self._reverse_adjacency[source].append((target, edge.edge_id))

        return edge

    def get_edge(self, edge_id: str) -> Optional[Edge]:
        """Get an edge."""
        return self._edges.get(edge_id)

    def neighbors(self, node_id: str) -> List[str]:
        """Get neighbors of a node."""
        return [n for n, _ in self._adjacency.get(node_id, [])]

    def predecessors(self, node_id: str) -> List[str]:
        """Get predecessors of a node."""
        return [n for n, _ in self._reverse_adjacency.get(node_id, [])]

    def all_nodes(self) -> List[Node]:
        """Get all nodes."""
        return list(self._nodes.values())

    def all_edges(self) -> List[Edge]:
        """Get all edges."""
        return list(self._edges.values())

    def node_count(self) -> int:
        """Get node count."""
        return len(self._nodes)

    def edge_count(self) -> int:
        """Get edge count."""
        return len(self._edges)


# =============================================================================
# PATH FINDER
# =============================================================================

class PathFinder:
    """Find paths in graphs."""

    def __init__(self, store: GraphStore):
        self._store = store

    def bfs(self, start: str, end: str) -> Optional[Path]:
        """Breadth-first search."""
        if start not in [n.node_id for n in self._store.all_nodes()]:
            return None

        visited = {start}
        queue = deque([(start, [start])])

        while queue:
            current, path = queue.popleft()

            if current == end:
                return Path(nodes=path)

            for neighbor in self._store.neighbors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None

    def dfs(self, start: str, end: str) -> Optional[Path]:
        """Depth-first search."""
        if start not in [n.node_id for n in self._store.all_nodes()]:
            return None

        visited = set()
        stack = [(start, [start])]

        while stack:
            current, path = stack.pop()

            if current == end:
                return Path(nodes=path)

            if current in visited:
                continue

            visited.add(current)

            for neighbor in self._store.neighbors(current):
                if neighbor not in visited:
                    stack.append((neighbor, path + [neighbor]))

        return None

    def dijkstra(self, start: str, end: str) -> Optional[Path]:
        """Dijkstra's shortest path."""
        distances: Dict[str, float] = {start: 0}
        previous: Dict[str, str] = {}
        pq = [(0, start)]
        visited = set()

        while pq:
            dist, current = heapq.heappop(pq)

            if current in visited:
                continue

            visited.add(current)

            if current == end:
                # Reconstruct path
                path = [end]
                while path[-1] in previous:
                    path.append(previous[path[-1]])
                path.reverse()

                return Path(nodes=path, total_weight=dist)

            for neighbor, edge_id in self._store._adjacency.get(current, []):
                edge = self._store.get_edge(edge_id)
                if not edge:
                    continue

                new_dist = dist + edge.weight

                if neighbor not in distances or new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    previous[neighbor] = current
                    heapq.heappush(pq, (new_dist, neighbor))

        return None

    def all_paths(
        self,
        start: str,
        end: str,
        max_length: int = 10
    ) -> List[Path]:
        """Find all paths up to max length."""
        paths = []
        stack = [(start, [start])]

        while stack:
            current, path = stack.pop()

            if len(path) > max_length:
                continue

            if current == end:
                paths.append(Path(nodes=path))
                continue

            for neighbor in self._store.neighbors(current):
                if neighbor not in path:
                    stack.append((neighbor, path + [neighbor]))

        return paths


# =============================================================================
# CENTRALITY ANALYZER
# =============================================================================

class CentralityAnalyzer:
    """Analyze node centrality."""

    def __init__(self, store: GraphStore):
        self._store = store

    def degree_centrality(self) -> CentralityResult:
        """Calculate degree centrality."""
        scores = {}
        n = self._store.node_count()

        if n <= 1:
            return CentralityResult(centrality_type=CentralityType.DEGREE)

        for node in self._store.all_nodes():
            out_degree = len(self._store.neighbors(node.node_id))
            in_degree = len(self._store.predecessors(node.node_id))
            scores[node.node_id] = (out_degree + in_degree) / (2 * (n - 1))

        return CentralityResult(
            centrality_type=CentralityType.DEGREE,
            scores=scores
        )

    def closeness_centrality(self) -> CentralityResult:
        """Calculate closeness centrality."""
        scores = {}
        nodes = self._store.all_nodes()
        n = len(nodes)

        if n <= 1:
            return CentralityResult(centrality_type=CentralityType.CLOSENESS)

        path_finder = PathFinder(self._store)

        for node in nodes:
            total_distance = 0
            reachable = 0

            for other in nodes:
                if node.node_id != other.node_id:
                    path = path_finder.bfs(node.node_id, other.node_id)
                    if path:
                        total_distance += len(path.nodes) - 1
                        reachable += 1

            if reachable > 0:
                scores[node.node_id] = reachable / total_distance
            else:
                scores[node.node_id] = 0.0

        return CentralityResult(
            centrality_type=CentralityType.CLOSENESS,
            scores=scores
        )

    def pagerank(
        self,
        damping: float = 0.85,
        iterations: int = 100
    ) -> CentralityResult:
        """Calculate PageRank."""
        nodes = self._store.all_nodes()
        n = len(nodes)

        if n == 0:
            return CentralityResult(centrality_type=CentralityType.PAGERANK)

        # Initialize
        scores = {node.node_id: 1.0 / n for node in nodes}

        for _ in range(iterations):
            new_scores = {}

            for node in nodes:
                rank = (1 - damping) / n

                for pred in self._store.predecessors(node.node_id):
                    out_degree = len(self._store.neighbors(pred))
                    if out_degree > 0:
                        rank += damping * scores[pred] / out_degree

                new_scores[node.node_id] = rank

            scores = new_scores

        return CentralityResult(
            centrality_type=CentralityType.PAGERANK,
            scores=scores
        )


# =============================================================================
# COMMUNITY DETECTOR
# =============================================================================

class CommunityDetector:
    """Detect communities in graphs."""

    def __init__(self, store: GraphStore):
        self._store = store

    def connected_components(self) -> List[Community]:
        """Find connected components."""
        visited = set()
        communities = []

        for node in self._store.all_nodes():
            if node.node_id in visited:
                continue

            # BFS to find component
            component = []
            queue = deque([node.node_id])

            while queue:
                current = queue.popleft()

                if current in visited:
                    continue

                visited.add(current)
                component.append(current)

                for neighbor in self._store.neighbors(current):
                    if neighbor not in visited:
                        queue.append(neighbor)

                for pred in self._store.predecessors(current):
                    if pred not in visited:
                        queue.append(pred)

            if component:
                # Calculate density
                n = len(component)
                edges = sum(
                    1 for e in self._store.all_edges()
                    if e.source in component and e.target in component
                )
                density = edges / (n * (n - 1)) if n > 1 else 0.0

                communities.append(Community(
                    nodes=component,
                    density=density
                ))

        return communities

    def label_propagation(self, iterations: int = 10) -> List[Community]:
        """Label propagation community detection."""
        nodes = self._store.all_nodes()

        # Initialize each node with unique label
        labels = {n.node_id: i for i, n in enumerate(nodes)}

        for _ in range(iterations):
            # Shuffle node order
            shuffled = list(nodes)
            random.shuffle(shuffled)

            for node in shuffled:
                # Count neighbor labels
                neighbor_labels = defaultdict(int)

                for neighbor in self._store.neighbors(node.node_id):
                    neighbor_labels[labels[neighbor]] += 1

                for pred in self._store.predecessors(node.node_id):
                    neighbor_labels[labels[pred]] += 1

                if neighbor_labels:
                    # Assign most common label
                    max_label = max(neighbor_labels.items(), key=lambda x: x[1])[0]
                    labels[node.node_id] = max_label

        # Group by label
        communities_map: Dict[int, List[str]] = defaultdict(list)
        for node_id, label in labels.items():
            communities_map[label].append(node_id)

        communities = []
        for nodes_list in communities_map.values():
            if nodes_list:
                n = len(nodes_list)
                edges = sum(
                    1 for e in self._store.all_edges()
                    if e.source in nodes_list and e.target in nodes_list
                )
                density = edges / (n * (n - 1)) if n > 1 else 0.0

                communities.append(Community(
                    nodes=nodes_list,
                    density=density
                ))

        return communities


# =============================================================================
# PATTERN MATCHER
# =============================================================================

class PatternMatcher:
    """Match patterns in graphs."""

    def __init__(self, store: GraphStore):
        self._store = store

    def find_triangles(self) -> List[Tuple[str, str, str]]:
        """Find all triangles."""
        triangles = []
        nodes = [n.node_id for n in self._store.all_nodes()]

        for i, n1 in enumerate(nodes):
            neighbors1 = set(self._store.neighbors(n1))

            for j, n2 in enumerate(nodes[i + 1:], i + 1):
                if n2 not in neighbors1:
                    continue

                neighbors2 = set(self._store.neighbors(n2))

                # Find common neighbors
                common = neighbors1 & neighbors2
                for n3 in common:
                    if n3 > n2:  # Avoid duplicates
                        triangles.append((n1, n2, n3))

        return triangles

    def find_cliques(self, min_size: int = 3) -> List[List[str]]:
        """Find cliques (simplified)."""
        # Start with triangles
        cliques = []
        triangles = self.find_triangles()

        for t in triangles:
            if len(t) >= min_size:
                cliques.append(list(t))

        return cliques


# =============================================================================
# GRAPH REASONER
# =============================================================================

class GraphReasoner:
    """
    Graph Reasoner for BAEL.

    Advanced graph-based reasoning and analysis.
    """

    def __init__(self):
        self._store = GraphStore()
        self._path_finder = PathFinder(self._store)
        self._centrality = CentralityAnalyzer(self._store)
        self._community = CommunityDetector(self._store)
        self._pattern = PatternMatcher(self._store)

    # -------------------------------------------------------------------------
    # GRAPH CONSTRUCTION
    # -------------------------------------------------------------------------

    def add_node(
        self,
        label: str,
        node_type: NodeType = NodeType.ENTITY,
        properties: Optional[Dict[str, Any]] = None
    ) -> Node:
        """Add a node."""
        return self._store.add_node(label, node_type, properties)

    def add_edge(
        self,
        source: str,
        target: str,
        label: str = "",
        weight: float = 1.0,
        edge_type: EdgeType = EdgeType.DIRECTED
    ) -> Edge:
        """Add an edge."""
        return self._store.add_edge(source, target, label, weight, edge_type)

    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node."""
        return self._store.get_node(node_id)

    def get_node_by_label(self, label: str) -> Optional[Node]:
        """Get a node by label."""
        return self._store.get_node_by_label(label)

    # -------------------------------------------------------------------------
    # PATH FINDING
    # -------------------------------------------------------------------------

    def find_path(
        self,
        start: str,
        end: str,
        algorithm: PathAlgorithm = PathAlgorithm.BFS
    ) -> Optional[Path]:
        """Find a path between nodes."""
        if algorithm == PathAlgorithm.BFS:
            return self._path_finder.bfs(start, end)
        elif algorithm == PathAlgorithm.DFS:
            return self._path_finder.dfs(start, end)
        elif algorithm == PathAlgorithm.DIJKSTRA:
            return self._path_finder.dijkstra(start, end)
        return None

    def shortest_path(self, start: str, end: str) -> Optional[Path]:
        """Find shortest path (unweighted)."""
        return self._path_finder.bfs(start, end)

    def weighted_shortest_path(self, start: str, end: str) -> Optional[Path]:
        """Find shortest weighted path."""
        return self._path_finder.dijkstra(start, end)

    # -------------------------------------------------------------------------
    # CENTRALITY
    # -------------------------------------------------------------------------

    def degree_centrality(self) -> CentralityResult:
        """Calculate degree centrality."""
        return self._centrality.degree_centrality()

    def closeness_centrality(self) -> CentralityResult:
        """Calculate closeness centrality."""
        return self._centrality.closeness_centrality()

    def pagerank(self, damping: float = 0.85) -> CentralityResult:
        """Calculate PageRank."""
        return self._centrality.pagerank(damping)

    # -------------------------------------------------------------------------
    # COMMUNITIES
    # -------------------------------------------------------------------------

    def find_communities(self) -> List[Community]:
        """Find communities using label propagation."""
        return self._community.label_propagation()

    def connected_components(self) -> List[Community]:
        """Find connected components."""
        return self._community.connected_components()

    # -------------------------------------------------------------------------
    # PATTERNS
    # -------------------------------------------------------------------------

    def find_triangles(self) -> List[Tuple[str, str, str]]:
        """Find triangles in the graph."""
        return self._pattern.find_triangles()

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        nodes = self._store.all_nodes()
        edges = self._store.all_edges()

        if not nodes:
            return {}

        return {
            "nodes": len(nodes),
            "edges": len(edges),
            "density": len(edges) / (len(nodes) * (len(nodes) - 1)) if len(nodes) > 1 else 0,
            "avg_degree": 2 * len(edges) / len(nodes) if nodes else 0
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Graph Reasoner."""
    print("=" * 70)
    print("BAEL - GRAPH REASONER DEMO")
    print("Advanced Graph-Based Reasoning and Analysis")
    print("=" * 70)
    print()

    reasoner = GraphReasoner()

    # 1. Build Graph
    print("1. BUILD GRAPH:")
    print("-" * 40)

    # Create a social network-like graph
    nodes = {}
    names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace"]

    for name in names:
        node = reasoner.add_node(name, NodeType.ENTITY, {"type": "person"})
        nodes[name] = node.node_id

    # Add connections
    connections = [
        ("Alice", "Bob"),
        ("Alice", "Charlie"),
        ("Bob", "Charlie"),
        ("Bob", "Diana"),
        ("Charlie", "Diana"),
        ("Diana", "Eve"),
        ("Eve", "Frank"),
        ("Frank", "Grace"),
        ("Grace", "Alice")
    ]

    for source, target in connections:
        reasoner.add_edge(
            nodes[source],
            nodes[target],
            "knows",
            weight=1.0,
            edge_type=EdgeType.UNDIRECTED
        )

    stats = reasoner.statistics()
    print(f"   Nodes: {stats['nodes']}")
    print(f"   Edges: {stats['edges']}")
    print(f"   Density: {stats['density']:.3f}")
    print(f"   Avg degree: {stats['avg_degree']:.2f}")
    print()

    # 2. Path Finding
    print("2. PATH FINDING:")
    print("-" * 40)

    path = reasoner.shortest_path(nodes["Alice"], nodes["Eve"])
    if path:
        path_names = [
            reasoner.get_node(nid).label if reasoner.get_node(nid) else nid
            for nid in path.nodes
        ]
        print(f"   Shortest path Alice -> Eve: {' -> '.join(path_names)}")

    path = reasoner.weighted_shortest_path(nodes["Alice"], nodes["Frank"])
    if path:
        path_names = [
            reasoner.get_node(nid).label if reasoner.get_node(nid) else nid
            for nid in path.nodes
        ]
        print(f"   Weighted shortest Alice -> Frank: {' -> '.join(path_names)}")
        print(f"   Total weight: {path.total_weight}")
    print()

    # 3. Degree Centrality
    print("3. DEGREE CENTRALITY:")
    print("-" * 40)

    result = reasoner.degree_centrality()
    sorted_scores = sorted(result.scores.items(), key=lambda x: -x[1])

    for node_id, score in sorted_scores[:5]:
        node = reasoner.get_node(node_id)
        print(f"   {node.label if node else node_id}: {score:.3f}")
    print()

    # 4. PageRank
    print("4. PAGERANK:")
    print("-" * 40)

    result = reasoner.pagerank(damping=0.85)
    sorted_scores = sorted(result.scores.items(), key=lambda x: -x[1])

    for node_id, score in sorted_scores[:5]:
        node = reasoner.get_node(node_id)
        print(f"   {node.label if node else node_id}: {score:.4f}")
    print()

    # 5. Connected Components
    print("5. CONNECTED COMPONENTS:")
    print("-" * 40)

    components = reasoner.connected_components()
    print(f"   Found {len(components)} component(s)")

    for i, comp in enumerate(components):
        comp_names = [
            reasoner.get_node(nid).label if reasoner.get_node(nid) else nid
            for nid in comp.nodes
        ]
        print(f"   Component {i + 1}: {comp_names}")
        print(f"      Density: {comp.density:.3f}")
    print()

    # 6. Community Detection
    print("6. COMMUNITY DETECTION:")
    print("-" * 40)

    communities = reasoner.find_communities()
    print(f"   Found {len(communities)} community(ies)")

    for i, comm in enumerate(communities):
        comm_names = [
            reasoner.get_node(nid).label if reasoner.get_node(nid) else nid
            for nid in comm.nodes
        ]
        print(f"   Community {i + 1}: {comm_names}")
    print()

    # 7. Triangle Detection
    print("7. TRIANGLE DETECTION:")
    print("-" * 40)

    triangles = reasoner.find_triangles()
    print(f"   Found {len(triangles)} triangle(s)")

    for t in triangles[:3]:
        t_names = [
            reasoner.get_node(nid).label if reasoner.get_node(nid) else nid
            for nid in t
        ]
        print(f"   Triangle: {t_names}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Graph Reasoner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
