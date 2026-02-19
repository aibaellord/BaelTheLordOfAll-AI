"""
🌐 NETWORK TOPOLOGY 🌐
======================
Network structure.

Features:
- Topology types
- Dynamic reconfiguration
- Optimization
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid
import math
import random


class TopologyType(Enum):
    """Network topology types"""
    MESH = auto()        # Fully connected
    RING = auto()        # Circular
    STAR = auto()        # Central hub
    TREE = auto()        # Hierarchical
    HYPERCUBE = auto()   # N-dimensional
    SMALL_WORLD = auto() # High clustering, short paths
    SCALE_FREE = auto()  # Power-law distribution


@dataclass
class NetworkEdge:
    """Edge between nodes"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    source_id: str = ""
    target_id: str = ""

    # Edge properties
    weight: float = 1.0
    latency_ms: float = 10.0
    bandwidth_mbps: float = 100.0

    # State
    active: bool = True

    # Metadata
    created_at: float = 0.0
    last_used: float = 0.0


class NetworkTopology:
    """
    Network topology manager.
    """

    def __init__(self, topology_type: TopologyType = TopologyType.MESH):
        self.topology_type = topology_type

        self.nodes: Set[str] = set()
        self.edges: Dict[str, NetworkEdge] = {}

        # Adjacency
        self.adjacency: Dict[str, Set[str]] = {}

    def add_node(self, node_id: str):
        """Add node"""
        self.nodes.add(node_id)
        if node_id not in self.adjacency:
            self.adjacency[node_id] = set()

    def remove_node(self, node_id: str):
        """Remove node"""
        if node_id not in self.nodes:
            return

        # Remove edges
        edges_to_remove = []
        for edge_id, edge in self.edges.items():
            if edge.source_id == node_id or edge.target_id == node_id:
                edges_to_remove.append(edge_id)

        for edge_id in edges_to_remove:
            del self.edges[edge_id]

        # Update adjacency
        for adjacent in self.adjacency.get(node_id, set()):
            self.adjacency[adjacent].discard(node_id)

        del self.adjacency[node_id]
        self.nodes.remove(node_id)

    def add_edge(self, source_id: str, target_id: str, **kwargs) -> NetworkEdge:
        """Add edge between nodes"""
        edge = NetworkEdge(
            source_id=source_id,
            target_id=target_id,
            **kwargs
        )

        self.edges[edge.id] = edge

        # Update adjacency
        if source_id not in self.adjacency:
            self.adjacency[source_id] = set()
        if target_id not in self.adjacency:
            self.adjacency[target_id] = set()

        self.adjacency[source_id].add(target_id)
        self.adjacency[target_id].add(source_id)

        return edge

    def get_neighbors(self, node_id: str) -> Set[str]:
        """Get node neighbors"""
        return self.adjacency.get(node_id, set())

    def get_edge(self, source_id: str, target_id: str) -> Optional[NetworkEdge]:
        """Get edge between nodes"""
        for edge in self.edges.values():
            if (edge.source_id == source_id and edge.target_id == target_id) or \
               (edge.source_id == target_id and edge.target_id == source_id):
                return edge
        return None

    def shortest_path(
        self,
        source_id: str,
        target_id: str
    ) -> List[str]:
        """Find shortest path (BFS)"""
        if source_id not in self.nodes or target_id not in self.nodes:
            return []

        if source_id == target_id:
            return [source_id]

        visited = {source_id}
        queue = [(source_id, [source_id])]

        while queue:
            current, path = queue.pop(0)

            for neighbor in self.get_neighbors(current):
                if neighbor == target_id:
                    return path + [neighbor]

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return []  # No path found

    def get_diameter(self) -> int:
        """Get network diameter (longest shortest path)"""
        max_dist = 0

        for source in self.nodes:
            for target in self.nodes:
                if source != target:
                    path = self.shortest_path(source, target)
                    if path:
                        max_dist = max(max_dist, len(path) - 1)

        return max_dist

    def get_clustering_coefficient(self, node_id: str) -> float:
        """Get local clustering coefficient"""
        neighbors = list(self.get_neighbors(node_id))
        n = len(neighbors)

        if n < 2:
            return 0.0

        # Count edges between neighbors
        edges = 0
        for i in range(n):
            for j in range(i + 1, n):
                if neighbors[j] in self.get_neighbors(neighbors[i]):
                    edges += 1

        possible = n * (n - 1) / 2
        return edges / possible if possible > 0 else 0.0


class TopologyOptimizer:
    """
    Optimize network topology.
    """

    def __init__(self, topology: NetworkTopology):
        self.topology = topology

    def optimize_for_latency(self):
        """Optimize for minimum latency"""
        # Add edges to reduce diameter
        nodes = list(self.topology.nodes)
        current_diameter = self.topology.get_diameter()

        if current_diameter > 3:
            # Add some long-range connections
            for _ in range(min(len(nodes), 5)):
                source = random.choice(nodes)
                target = random.choice(nodes)

                if source != target and target not in self.topology.get_neighbors(source):
                    self.topology.add_edge(source, target)

    def optimize_for_resilience(self):
        """Optimize for fault tolerance"""
        # Ensure minimum connectivity
        nodes = list(self.topology.nodes)

        for node_id in nodes:
            neighbors = self.topology.get_neighbors(node_id)

            # Each node should have at least 2 connections
            while len(neighbors) < 2 and len(nodes) > 2:
                candidates = [n for n in nodes if n != node_id and n not in neighbors]
                if candidates:
                    target = random.choice(candidates)
                    self.topology.add_edge(node_id, target)
                    neighbors = self.topology.get_neighbors(node_id)
                else:
                    break

    def prune_redundant_edges(self, max_degree: int = 10):
        """Remove redundant edges"""
        for node_id in self.topology.nodes:
            neighbors = list(self.topology.get_neighbors(node_id))

            while len(neighbors) > max_degree:
                # Remove highest latency edge
                max_latency = 0
                worst_neighbor = None

                for neighbor in neighbors:
                    edge = self.topology.get_edge(node_id, neighbor)
                    if edge and edge.latency_ms > max_latency:
                        max_latency = edge.latency_ms
                        worst_neighbor = neighbor

                if worst_neighbor:
                    # Find and remove edge
                    for edge_id, edge in list(self.topology.edges.items()):
                        if (edge.source_id == node_id and edge.target_id == worst_neighbor) or \
                           (edge.source_id == worst_neighbor and edge.target_id == node_id):
                            del self.topology.edges[edge_id]
                            self.topology.adjacency[node_id].discard(worst_neighbor)
                            self.topology.adjacency[worst_neighbor].discard(node_id)
                            break

                neighbors = list(self.topology.get_neighbors(node_id))


class DynamicTopology(NetworkTopology):
    """
    Self-adapting network topology.
    """

    def __init__(self, topology_type: TopologyType = TopologyType.SMALL_WORLD):
        super().__init__(topology_type)

        self.optimizer = TopologyOptimizer(self)

        # Metrics for adaptation
        self.edge_usage: Dict[str, int] = {}
        self.path_latencies: List[float] = []

    def record_usage(self, edge_id: str):
        """Record edge usage"""
        if edge_id not in self.edge_usage:
            self.edge_usage[edge_id] = 0
        self.edge_usage[edge_id] += 1

    def record_path_latency(self, latency_ms: float):
        """Record path latency"""
        self.path_latencies.append(latency_ms)

        # Keep last 1000
        if len(self.path_latencies) > 1000:
            self.path_latencies = self.path_latencies[-1000:]

    def adapt(self):
        """Adapt topology based on usage"""
        # Remove unused edges
        unused = [
            edge_id for edge_id, usage in self.edge_usage.items()
            if usage == 0
        ]

        for edge_id in unused[:len(unused)//4]:  # Remove up to 25%
            if edge_id in self.edges:
                edge = self.edges[edge_id]

                # Don't disconnect nodes
                if len(self.get_neighbors(edge.source_id)) > 2 and \
                   len(self.get_neighbors(edge.target_id)) > 2:
                    del self.edges[edge_id]
                    self.adjacency[edge.source_id].discard(edge.target_id)
                    self.adjacency[edge.target_id].discard(edge.source_id)

        # Add edges on hot paths
        high_usage = sorted(
            self.edge_usage.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        for edge_id, usage in high_usage:
            if edge_id in self.edges:
                edge = self.edges[edge_id]
                # Reduce latency weight for hot edges
                edge.weight *= 0.9

        # Reset usage counts
        self.edge_usage = {}

        # Check if latency optimization needed
        if self.path_latencies:
            avg_latency = sum(self.path_latencies) / len(self.path_latencies)
            if avg_latency > 100:  # ms
                self.optimizer.optimize_for_latency()

    def generate_small_world(self, k: int = 4, p: float = 0.1):
        """Generate small-world topology (Watts-Strogatz)"""
        nodes = list(self.nodes)
        n = len(nodes)

        if n < k + 1:
            return

        # Create ring lattice
        for i in range(n):
            for j in range(1, k // 2 + 1):
                target = (i + j) % n
                if nodes[target] not in self.get_neighbors(nodes[i]):
                    self.add_edge(nodes[i], nodes[target])

        # Rewire with probability p
        for edge_id in list(self.edges.keys()):
            if random.random() < p:
                edge = self.edges[edge_id]
                source = edge.source_id

                # Choose new target
                candidates = [n for n in nodes if n != source and n not in self.get_neighbors(source)]
                if candidates:
                    new_target = random.choice(candidates)

                    # Remove old edge
                    old_target = edge.target_id
                    del self.edges[edge_id]
                    self.adjacency[source].discard(old_target)
                    self.adjacency[old_target].discard(source)

                    # Add new edge
                    self.add_edge(source, new_target)

    def get_topology_stats(self) -> Dict[str, Any]:
        """Get topology statistics"""
        avg_clustering = 0.0
        if self.nodes:
            avg_clustering = sum(
                self.get_clustering_coefficient(n) for n in self.nodes
            ) / len(self.nodes)

        avg_degree = 0.0
        if self.nodes:
            avg_degree = sum(
                len(self.get_neighbors(n)) for n in self.nodes
            ) / len(self.nodes)

        return {
            'type': self.topology_type.name,
            'nodes': len(self.nodes),
            'edges': len(self.edges),
            'diameter': self.get_diameter(),
            'avg_clustering': avg_clustering,
            'avg_degree': avg_degree,
            'avg_path_latency': (
                sum(self.path_latencies) / len(self.path_latencies)
                if self.path_latencies else 0
            )
        }


# Export all
__all__ = [
    'TopologyType',
    'NetworkEdge',
    'NetworkTopology',
    'TopologyOptimizer',
    'DynamicTopology',
]
