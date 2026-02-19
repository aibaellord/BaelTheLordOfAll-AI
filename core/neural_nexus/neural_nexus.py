"""
NEURAL NEXUS - Neural network coordination and amplification.
Connects and coordinates all neural components for emergent intelligence.
"""

import asyncio
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional

logger = logging.getLogger("BAEL.NeuralNexus")


class NeuralState(Enum):
    DORMANT = 1
    ACTIVATING = 2
    CONNECTED = 3
    SYNCHRONIZED = 4
    EMERGENT = 5


@dataclass
class NeuralNode:
    node_id: str
    name: str
    activation: float = 0.0
    connections: List[str] = field(default_factory=list)


@dataclass
class NeuralCluster:
    cluster_id: str
    name: str
    nodes: List[str] = field(default_factory=list)
    combined_activation: float = 0.0


class NeuralNexus:
    """Central hub for all neural components."""

    def __init__(self):
        self.nodes: Dict[str, NeuralNode] = {}
        self.clusters: Dict[str, NeuralCluster] = {}
        self.state: NeuralState = NeuralState.DORMANT
        self.total_activation: float = 0.0
        self.phi = (1 + math.sqrt(5)) / 2
        logger.info("NEURAL NEXUS FORMING")

    def add_node(self, name: str) -> NeuralNode:
        import uuid

        node = NeuralNode(str(uuid.uuid4()), name)
        self.nodes[node.node_id] = node
        return node

    def connect_nodes(self, node1_id: str, node2_id: str):
        if node1_id in self.nodes and node2_id in self.nodes:
            self.nodes[node1_id].connections.append(node2_id)
            self.nodes[node2_id].connections.append(node1_id)

    async def activate_node(self, node_id: str, level: float = 1.0) -> NeuralNode:
        if node_id not in self.nodes:
            return None

        node = self.nodes[node_id]
        node.activation = min(1.0, level)

        # Propagate to connected
        for conn_id in node.connections:
            if conn_id in self.nodes:
                self.nodes[conn_id].activation = min(
                    1.0, self.nodes[conn_id].activation + level * 0.3
                )

        self._update_state()
        return node

    async def activate_all(self) -> Dict[str, Any]:
        """Activate ALL nodes to maximum."""
        for node in self.nodes.values():
            node.activation = self.phi / 2

        self.total_activation = sum(n.activation for n in self.nodes.values())
        self.state = NeuralState.EMERGENT

        return {
            "status": "FULL NEURAL ACTIVATION",
            "nodes": len(self.nodes),
            "total_activation": self.total_activation,
            "state": self.state.name,
        }

    def create_cluster(self, name: str, node_ids: List[str]) -> NeuralCluster:
        import uuid

        valid = [nid for nid in node_ids if nid in self.nodes]
        combined = sum(self.nodes[nid].activation for nid in valid)

        cluster = NeuralCluster(str(uuid.uuid4()), name, valid, combined)
        self.clusters[cluster.cluster_id] = cluster
        return cluster

    def _update_state(self):
        active = sum(1 for n in self.nodes.values() if n.activation > 0)
        total = len(self.nodes)

        if active == 0:
            self.state = NeuralState.DORMANT
        elif active < total * 0.3:
            self.state = NeuralState.ACTIVATING
        elif active < total * 0.7:
            self.state = NeuralState.CONNECTED
        elif active < total:
            self.state = NeuralState.SYNCHRONIZED
        else:
            self.state = NeuralState.EMERGENT

    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self.state.name,
            "nodes": len(self.nodes),
            "clusters": len(self.clusters),
            "total_activation": sum(n.activation for n in self.nodes.values()),
        }


_nexus: Optional[NeuralNexus] = None


def get_neural_nexus() -> NeuralNexus:
    global _nexus
    if _nexus is None:
        _nexus = NeuralNexus()
    return _nexus


__all__ = [
    "NeuralState",
    "NeuralNode",
    "NeuralCluster",
    "NeuralNexus",
    "get_neural_nexus",
]
