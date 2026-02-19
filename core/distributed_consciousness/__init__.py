"""
🌐 DISTRIBUTED CONSCIOUSNESS NETWORK 🌐
========================================
Multi-node awareness system.

Features:
- Distributed processing
- Node coordination
- Collective intelligence
- Consensus mechanisms
"""

from .node_core import (
    NodeState,
    NodeCapability,
    ConsciousnessNode,
    NodeRegistry,
    NodeDiscovery,
)

from .network_topology import (
    TopologyType,
    NetworkEdge,
    NetworkTopology,
    TopologyOptimizer,
    DynamicTopology,
)

from .consensus import (
    ConsensusType,
    Vote,
    Proposal,
    ConsensusProtocol,
    PBFTConsensus,
    RaftConsensus,
)

from .distributed_memory import (
    MemorySegment,
    SharedMemory,
    DistributedCache,
    MemoryConsistency,
    EventualConsistency,
)

from .collective_intelligence import (
    CollectiveThought,
    SwarmDecision,
    EmergentPattern,
    CollectiveIntelligence,
    HiveMind,
)

__all__ = [
    # Node Core
    'NodeState',
    'NodeCapability',
    'ConsciousnessNode',
    'NodeRegistry',
    'NodeDiscovery',

    # Network Topology
    'TopologyType',
    'NetworkEdge',
    'NetworkTopology',
    'TopologyOptimizer',
    'DynamicTopology',

    # Consensus
    'ConsensusType',
    'Vote',
    'Proposal',
    'ConsensusProtocol',
    'PBFTConsensus',
    'RaftConsensus',

    # Distributed Memory
    'MemorySegment',
    'SharedMemory',
    'DistributedCache',
    'MemoryConsistency',
    'EventualConsistency',

    # Collective Intelligence
    'CollectiveThought',
    'SwarmDecision',
    'EmergentPattern',
    'CollectiveIntelligence',
    'HiveMind',
]
