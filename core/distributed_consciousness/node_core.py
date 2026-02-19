"""
🌐 NODE CORE 🌐
===============
Consciousness nodes.

Features:
- Node state
- Capabilities
- Discovery
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Callable
from datetime import datetime
import uuid
import hashlib


class NodeState(Enum):
    """Node states"""
    INITIALIZING = auto()
    READY = auto()
    ACTIVE = auto()
    BUSY = auto()
    DEGRADED = auto()
    OFFLINE = auto()
    FAILED = auto()


@dataclass
class NodeCapability:
    """A node capability"""
    name: str = ""
    version: str = "1.0"

    # Performance
    throughput: float = 1.0
    latency_ms: float = 10.0

    # Resource requirements
    memory_mb: int = 0
    compute_units: int = 1

    # Availability
    available: bool = True


@dataclass
class ConsciousnessNode:
    """A consciousness network node"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""

    # State
    state: NodeState = NodeState.INITIALIZING

    # Capabilities
    capabilities: Dict[str, NodeCapability] = field(default_factory=dict)

    # Resources
    total_memory_mb: int = 1024
    available_memory_mb: int = 1024
    total_compute_units: int = 10
    available_compute_units: int = 10

    # Health
    health_score: float = 1.0
    last_heartbeat: datetime = field(default_factory=datetime.now)
    uptime_seconds: int = 0

    # Network
    address: str = ""
    port: int = 0
    connected_nodes: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update_heartbeat(self):
        """Update heartbeat"""
        now = datetime.now()
        self.uptime_seconds += int((now - self.last_heartbeat).total_seconds())
        self.last_heartbeat = now

    def add_capability(self, capability: NodeCapability):
        """Add capability"""
        self.capabilities[capability.name] = capability

    def has_capability(self, name: str) -> bool:
        """Check if node has capability"""
        return name in self.capabilities and self.capabilities[name].available

    def allocate_resources(self, memory_mb: int, compute_units: int) -> bool:
        """Allocate resources"""
        if memory_mb > self.available_memory_mb:
            return False
        if compute_units > self.available_compute_units:
            return False

        self.available_memory_mb -= memory_mb
        self.available_compute_units -= compute_units
        return True

    def release_resources(self, memory_mb: int, compute_units: int):
        """Release resources"""
        self.available_memory_mb = min(self.total_memory_mb, self.available_memory_mb + memory_mb)
        self.available_compute_units = min(self.total_compute_units, self.available_compute_units + compute_units)

    def get_load(self) -> float:
        """Get current load (0-1)"""
        memory_load = 1 - (self.available_memory_mb / self.total_memory_mb)
        compute_load = 1 - (self.available_compute_units / self.total_compute_units)
        return (memory_load + compute_load) / 2

    def can_accept_work(self) -> bool:
        """Check if node can accept work"""
        return (
            self.state == NodeState.READY and
            self.get_load() < 0.9 and
            self.health_score > 0.5
        )

    def set_state(self, state: NodeState):
        """Set node state"""
        self.state = state


class NodeRegistry:
    """
    Registry of consciousness nodes.
    """

    def __init__(self):
        self.nodes: Dict[str, ConsciousnessNode] = {}

        # Indexing
        self.by_capability: Dict[str, List[str]] = {}
        self.by_state: Dict[NodeState, List[str]] = {}

        # Callbacks
        self.on_register: List[Callable[[ConsciousnessNode], None]] = []
        self.on_unregister: List[Callable[[str], None]] = []

    def register(self, node: ConsciousnessNode):
        """Register node"""
        self.nodes[node.id] = node

        # Index by capability
        for cap_name in node.capabilities:
            if cap_name not in self.by_capability:
                self.by_capability[cap_name] = []
            self.by_capability[cap_name].append(node.id)

        # Index by state
        if node.state not in self.by_state:
            self.by_state[node.state] = []
        self.by_state[node.state].append(node.id)

        # Callbacks
        for callback in self.on_register:
            callback(node)

    def unregister(self, node_id: str):
        """Unregister node"""
        if node_id not in self.nodes:
            return

        node = self.nodes[node_id]

        # Remove from indices
        for cap_name in node.capabilities:
            if cap_name in self.by_capability:
                self.by_capability[cap_name] = [
                    nid for nid in self.by_capability[cap_name]
                    if nid != node_id
                ]

        if node.state in self.by_state:
            self.by_state[node.state] = [
                nid for nid in self.by_state[node.state]
                if nid != node_id
            ]

        del self.nodes[node_id]

        # Callbacks
        for callback in self.on_unregister:
            callback(node_id)

    def get(self, node_id: str) -> Optional[ConsciousnessNode]:
        """Get node by ID"""
        return self.nodes.get(node_id)

    def find_by_capability(self, capability: str) -> List[ConsciousnessNode]:
        """Find nodes with capability"""
        node_ids = self.by_capability.get(capability, [])
        return [self.nodes[nid] for nid in node_ids if nid in self.nodes]

    def find_by_state(self, state: NodeState) -> List[ConsciousnessNode]:
        """Find nodes in state"""
        node_ids = self.by_state.get(state, [])
        return [self.nodes[nid] for nid in node_ids if nid in self.nodes]

    def find_available(
        self,
        capability: str = None,
        min_memory: int = 0,
        min_compute: int = 0
    ) -> List[ConsciousnessNode]:
        """Find available nodes"""
        candidates = list(self.nodes.values())

        # Filter by state
        candidates = [n for n in candidates if n.can_accept_work()]

        # Filter by capability
        if capability:
            candidates = [n for n in candidates if n.has_capability(capability)]

        # Filter by resources
        candidates = [
            n for n in candidates
            if n.available_memory_mb >= min_memory and
               n.available_compute_units >= min_compute
        ]

        # Sort by load (least loaded first)
        candidates.sort(key=lambda n: n.get_load())

        return candidates

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        return {
            'total_nodes': len(self.nodes),
            'by_state': {
                state.name: len(node_ids)
                for state, node_ids in self.by_state.items()
            },
            'capabilities': list(self.by_capability.keys()),
            'total_compute': sum(n.total_compute_units for n in self.nodes.values()),
            'available_compute': sum(n.available_compute_units for n in self.nodes.values()),
        }


class NodeDiscovery:
    """
    Node discovery service.
    """

    def __init__(self, registry: NodeRegistry):
        self.registry = registry

        # Discovery methods
        self.discovery_methods: List[Callable[[], List[ConsciousnessNode]]] = []

        # Known addresses
        self.known_addresses: Set[str] = set()

        # Discovery interval
        self.discovery_interval_seconds: int = 30

        # Last discovery
        self.last_discovery: Optional[datetime] = None

    def add_discovery_method(self, method: Callable[[], List[ConsciousnessNode]]):
        """Add discovery method"""
        self.discovery_methods.append(method)

    def discover(self) -> List[ConsciousnessNode]:
        """Run discovery"""
        discovered = []

        for method in self.discovery_methods:
            try:
                nodes = method()
                for node in nodes:
                    if node.id not in self.registry.nodes:
                        self.registry.register(node)
                        discovered.append(node)

                        if node.address:
                            self.known_addresses.add(f"{node.address}:{node.port}")
            except Exception:
                pass

        self.last_discovery = datetime.now()
        return discovered

    def announce(self, node: ConsciousnessNode):
        """Announce node presence"""
        # In a real implementation, this would broadcast to the network
        self.registry.register(node)

    def check_liveness(self) -> List[str]:
        """Check node liveness, return failed nodes"""
        failed = []
        now = datetime.now()

        for node in list(self.registry.nodes.values()):
            # Check heartbeat timeout (60 seconds)
            delta = (now - node.last_heartbeat).total_seconds()
            if delta > 60:
                node.state = NodeState.FAILED
                failed.append(node.id)

        return failed

    def get_network_topology(self) -> Dict[str, List[str]]:
        """Get current network topology"""
        topology = {}

        for node in self.registry.nodes.values():
            topology[node.id] = node.connected_nodes.copy()

        return topology


# Export all
__all__ = [
    'NodeState',
    'NodeCapability',
    'ConsciousnessNode',
    'NodeRegistry',
    'NodeDiscovery',
]
