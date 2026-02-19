"""
BAEL Graph Store
=================

Storage and querying for knowledge graphs.
Enables graph-based knowledge management.

Features:
- Node and edge storage
- Graph traversal
- Subgraph extraction
- Persistence
- Indexing
"""

import hashlib
import json
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    """A node in the knowledge graph."""
    id: str
    label: str

    # Type
    node_type: str = "entity"

    # Properties
    properties: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, GraphNode):
            return self.id == other.id
        return False


@dataclass
class GraphEdge:
    """An edge in the knowledge graph."""
    id: str
    source_id: str
    target_id: str
    label: str

    # Properties
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)

    # Direction
    bidirectional: bool = False

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SubGraph:
    """A subgraph extracted from the main graph."""
    nodes: List[GraphNode] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)

    # Metadata
    root_id: Optional[str] = None
    depth: int = 0

    def node_count(self) -> int:
        return len(self.nodes)

    def edge_count(self) -> int:
        return len(self.edges)


class GraphStore:
    """
    Graph store for BAEL.

    Stores and queries knowledge graphs.
    """

    def __init__(self):
        # Storage
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: Dict[str, GraphEdge] = {}

        # Indexes
        self._outgoing: Dict[str, List[str]] = defaultdict(list)  # node_id -> [edge_ids]
        self._incoming: Dict[str, List[str]] = defaultdict(list)  # node_id -> [edge_ids]
        self._by_type: Dict[str, Set[str]] = defaultdict(set)  # type -> {node_ids}
        self._by_label: Dict[str, Set[str]] = defaultdict(set)  # label -> {node_ids}

        # Stats
        self.stats = {
            "nodes_added": 0,
            "edges_added": 0,
            "queries_executed": 0,
        }

    def add_node(
        self,
        label: str,
        node_type: str = "entity",
        properties: Optional[Dict[str, Any]] = None,
        node_id: Optional[str] = None,
    ) -> GraphNode:
        """
        Add a node to the graph.

        Args:
            label: Node label
            node_type: Node type
            properties: Node properties
            node_id: Optional custom ID

        Returns:
            Created node
        """
        node_id = node_id or hashlib.md5(
            f"{label}:{node_type}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        node = GraphNode(
            id=node_id,
            label=label,
            node_type=node_type,
            properties=properties or {},
        )

        self._nodes[node_id] = node
        self._by_type[node_type].add(node_id)
        self._by_label[label.lower()].add(node_id)

        self.stats["nodes_added"] += 1

        return node

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        label: str,
        weight: float = 1.0,
        properties: Optional[Dict[str, Any]] = None,
        bidirectional: bool = False,
    ) -> Optional[GraphEdge]:
        """
        Add an edge to the graph.

        Args:
            source_id: Source node ID
            target_id: Target node ID
            label: Edge label
            weight: Edge weight
            properties: Edge properties
            bidirectional: Is edge bidirectional

        Returns:
            Created edge or None if nodes don't exist
        """
        if source_id not in self._nodes or target_id not in self._nodes:
            return None

        edge_id = hashlib.md5(
            f"{source_id}:{label}:{target_id}".encode()
        ).hexdigest()[:12]

        edge = GraphEdge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            label=label,
            weight=weight,
            properties=properties or {},
            bidirectional=bidirectional,
        )

        self._edges[edge_id] = edge
        self._outgoing[source_id].append(edge_id)
        self._incoming[target_id].append(edge_id)

        if bidirectional:
            self._outgoing[target_id].append(edge_id)
            self._incoming[source_id].append(edge_id)

        self.stats["edges_added"] += 1

        return edge

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def get_edge(self, edge_id: str) -> Optional[GraphEdge]:
        """Get an edge by ID."""
        return self._edges.get(edge_id)

    def find_nodes(
        self,
        label: Optional[str] = None,
        node_type: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> List[GraphNode]:
        """
        Find nodes matching criteria.

        Args:
            label: Label to match
            node_type: Type to match
            properties: Properties to match

        Returns:
            Matching nodes
        """
        self.stats["queries_executed"] += 1

        # Start with all nodes or filtered by type
        if node_type:
            node_ids = self._by_type.get(node_type, set())
        else:
            node_ids = set(self._nodes.keys())

        # Filter by label
        if label:
            label_ids = self._by_label.get(label.lower(), set())
            node_ids = node_ids & label_ids

        # Get nodes
        nodes = [self._nodes[nid] for nid in node_ids]

        # Filter by properties
        if properties:
            nodes = [
                n for n in nodes
                if all(n.properties.get(k) == v for k, v in properties.items())
            ]

        return nodes

    def get_neighbors(
        self,
        node_id: str,
        direction: str = "both",  # "out", "in", "both"
        edge_label: Optional[str] = None,
    ) -> List[GraphNode]:
        """
        Get neighboring nodes.

        Args:
            node_id: Source node ID
            direction: Direction to traverse
            edge_label: Filter by edge label

        Returns:
            Neighbor nodes
        """
        neighbors = []

        if direction in ["out", "both"]:
            for edge_id in self._outgoing.get(node_id, []):
                edge = self._edges.get(edge_id)
                if edge and (not edge_label or edge.label == edge_label):
                    if edge.target_id != node_id:
                        neighbor = self._nodes.get(edge.target_id)
                    else:
                        neighbor = self._nodes.get(edge.source_id)
                    if neighbor:
                        neighbors.append(neighbor)

        if direction in ["in", "both"]:
            for edge_id in self._incoming.get(node_id, []):
                edge = self._edges.get(edge_id)
                if edge and (not edge_label or edge.label == edge_label):
                    if edge.source_id != node_id:
                        neighbor = self._nodes.get(edge.source_id)
                    else:
                        neighbor = self._nodes.get(edge.target_id)
                    if neighbor and neighbor not in neighbors:
                        neighbors.append(neighbor)

        return neighbors

    def get_edges_for_node(
        self,
        node_id: str,
        direction: str = "both",
    ) -> List[GraphEdge]:
        """Get edges connected to a node."""
        edges = []

        if direction in ["out", "both"]:
            for edge_id in self._outgoing.get(node_id, []):
                edge = self._edges.get(edge_id)
                if edge:
                    edges.append(edge)

        if direction in ["in", "both"]:
            for edge_id in self._incoming.get(node_id, []):
                edge = self._edges.get(edge_id)
                if edge and edge not in edges:
                    edges.append(edge)

        return edges

    def traverse_bfs(
        self,
        start_id: str,
        max_depth: int = 3,
        edge_filter: Optional[Callable[[GraphEdge], bool]] = None,
    ) -> SubGraph:
        """
        Traverse graph using BFS.

        Args:
            start_id: Starting node ID
            max_depth: Maximum traversal depth
            edge_filter: Optional edge filter function

        Returns:
            Subgraph containing traversed nodes and edges
        """
        if start_id not in self._nodes:
            return SubGraph()

        visited_nodes: Set[str] = set()
        visited_edges: Set[str] = set()

        queue = deque([(start_id, 0)])
        visited_nodes.add(start_id)

        while queue:
            node_id, depth = queue.popleft()

            if depth >= max_depth:
                continue

            # Get outgoing edges
            for edge_id in self._outgoing.get(node_id, []):
                edge = self._edges.get(edge_id)
                if not edge:
                    continue

                if edge_filter and not edge_filter(edge):
                    continue

                visited_edges.add(edge_id)

                target_id = edge.target_id if edge.source_id == node_id else edge.source_id

                if target_id not in visited_nodes:
                    visited_nodes.add(target_id)
                    queue.append((target_id, depth + 1))

        return SubGraph(
            nodes=[self._nodes[nid] for nid in visited_nodes],
            edges=[self._edges[eid] for eid in visited_edges],
            root_id=start_id,
            depth=max_depth,
        )

    def traverse_dfs(
        self,
        start_id: str,
        max_depth: int = 3,
        edge_filter: Optional[Callable[[GraphEdge], bool]] = None,
    ) -> SubGraph:
        """
        Traverse graph using DFS.

        Args:
            start_id: Starting node ID
            max_depth: Maximum traversal depth
            edge_filter: Optional edge filter function

        Returns:
            Subgraph containing traversed nodes and edges
        """
        if start_id not in self._nodes:
            return SubGraph()

        visited_nodes: Set[str] = set()
        visited_edges: Set[str] = set()

        def dfs(node_id: str, depth: int):
            if depth > max_depth or node_id in visited_nodes:
                return

            visited_nodes.add(node_id)

            for edge_id in self._outgoing.get(node_id, []):
                edge = self._edges.get(edge_id)
                if not edge:
                    continue

                if edge_filter and not edge_filter(edge):
                    continue

                visited_edges.add(edge_id)

                target_id = edge.target_id if edge.source_id == node_id else edge.source_id
                dfs(target_id, depth + 1)

        dfs(start_id, 0)

        return SubGraph(
            nodes=[self._nodes[nid] for nid in visited_nodes],
            edges=[self._edges[eid] for eid in visited_edges],
            root_id=start_id,
            depth=max_depth,
        )

    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 10,
    ) -> Optional[List[GraphNode]]:
        """
        Find shortest path between nodes.

        Args:
            source_id: Source node ID
            target_id: Target node ID
            max_depth: Maximum path length

        Returns:
            Path as list of nodes or None
        """
        if source_id not in self._nodes or target_id not in self._nodes:
            return None

        if source_id == target_id:
            return [self._nodes[source_id]]

        visited = {source_id}
        queue = deque([(source_id, [self._nodes[source_id]])])

        while queue:
            node_id, path = queue.popleft()

            if len(path) > max_depth:
                continue

            for edge_id in self._outgoing.get(node_id, []):
                edge = self._edges.get(edge_id)
                if not edge:
                    continue

                next_id = edge.target_id if edge.source_id == node_id else edge.source_id

                if next_id == target_id:
                    return path + [self._nodes[target_id]]

                if next_id not in visited:
                    visited.add(next_id)
                    queue.append((next_id, path + [self._nodes[next_id]]))

        return None

    def delete_node(self, node_id: str) -> bool:
        """Delete a node and its edges."""
        if node_id not in self._nodes:
            return False

        node = self._nodes[node_id]

        # Delete connected edges
        for edge_id in list(self._outgoing.get(node_id, [])):
            self.delete_edge(edge_id)

        for edge_id in list(self._incoming.get(node_id, [])):
            self.delete_edge(edge_id)

        # Remove from indexes
        self._by_type[node.node_type].discard(node_id)
        self._by_label[node.label.lower()].discard(node_id)

        # Delete node
        del self._nodes[node_id]

        return True

    def delete_edge(self, edge_id: str) -> bool:
        """Delete an edge."""
        if edge_id not in self._edges:
            return False

        edge = self._edges[edge_id]

        # Remove from indexes
        if edge_id in self._outgoing.get(edge.source_id, []):
            self._outgoing[edge.source_id].remove(edge_id)
        if edge_id in self._incoming.get(edge.target_id, []):
            self._incoming[edge.target_id].remove(edge_id)

        if edge.bidirectional:
            if edge_id in self._outgoing.get(edge.target_id, []):
                self._outgoing[edge.target_id].remove(edge_id)
            if edge_id in self._incoming.get(edge.source_id, []):
                self._incoming[edge.source_id].remove(edge_id)

        del self._edges[edge_id]

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Export graph to dictionary."""
        return {
            "nodes": [
                {
                    "id": n.id,
                    "label": n.label,
                    "type": n.node_type,
                    "properties": n.properties,
                }
                for n in self._nodes.values()
            ],
            "edges": [
                {
                    "id": e.id,
                    "source": e.source_id,
                    "target": e.target_id,
                    "label": e.label,
                    "weight": e.weight,
                    "properties": e.properties,
                }
                for e in self._edges.values()
            ],
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Import graph from dictionary."""
        for node_data in data.get("nodes", []):
            self.add_node(
                label=node_data["label"],
                node_type=node_data.get("type", "entity"),
                properties=node_data.get("properties", {}),
                node_id=node_data["id"],
            )

        for edge_data in data.get("edges", []):
            self.add_edge(
                source_id=edge_data["source"],
                target_id=edge_data["target"],
                label=edge_data["label"],
                weight=edge_data.get("weight", 1.0),
                properties=edge_data.get("properties", {}),
            )

    def clear(self) -> None:
        """Clear the graph."""
        self._nodes.clear()
        self._edges.clear()
        self._outgoing.clear()
        self._incoming.clear()
        self._by_type.clear()
        self._by_label.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            **self.stats,
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "node_types": len(self._by_type),
        }


def demo():
    """Demonstrate graph store."""
    print("=" * 60)
    print("BAEL Graph Store Demo")
    print("=" * 60)

    store = GraphStore()

    # Add nodes
    print("\nAdding nodes...")
    python = store.add_node("Python", "language", {"version": "3.11"})
    tensorflow = store.add_node("TensorFlow", "framework")
    pytorch = store.add_node("PyTorch", "framework")
    google = store.add_node("Google", "organization")
    meta = store.add_node("Meta", "organization")
    ml = store.add_node("Machine Learning", "concept")

    print(f"  Added {store.stats['nodes_added']} nodes")

    # Add edges
    print("\nAdding edges...")
    store.add_edge(tensorflow.id, python.id, "built_with")
    store.add_edge(pytorch.id, python.id, "built_with")
    store.add_edge(google.id, tensorflow.id, "created")
    store.add_edge(meta.id, pytorch.id, "created")
    store.add_edge(tensorflow.id, ml.id, "used_for")
    store.add_edge(pytorch.id, ml.id, "used_for")

    print(f"  Added {store.stats['edges_added']} edges")

    # Query
    print("\nQuerying...")
    frameworks = store.find_nodes(node_type="framework")
    print(f"  Frameworks: {[f.label for f in frameworks]}")

    # Traverse
    print("\nTraversing from TensorFlow...")
    subgraph = store.traverse_bfs(tensorflow.id, max_depth=2)
    print(f"  Found {subgraph.node_count()} nodes, {subgraph.edge_count()} edges")
    for node in subgraph.nodes:
        print(f"    - {node.label} ({node.node_type})")

    # Find path
    print("\nFinding path from Google to Python...")
    path = store.find_path(google.id, python.id)
    if path:
        print(f"  Path: {' -> '.join(n.label for n in path)}")

    # Get neighbors
    print("\nNeighbors of Python...")
    neighbors = store.get_neighbors(python.id)
    print(f"  {[n.label for n in neighbors]}")

    print(f"\nStats: {store.get_stats()}")


if __name__ == "__main__":
    demo()
