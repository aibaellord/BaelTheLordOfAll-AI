"""
⚡ SWARM CONSCIOUSNESS MATRIX ⚡
===============================
Multi-agent emergent intelligence through swarm dynamics.

This module implements genuine swarm intelligence algorithms:
- Stigmergy (indirect coordination through environment)
- Ant Colony Optimization (pheromone-based pathfinding)
- Particle Swarm Optimization (velocity-based search)
- Self-Organizing Criticality (edge-of-chaos dynamics)
- Collective Decision Making
"""

from .swarm_core import (
    SwarmAgent,
    SwarmMessage,
    SwarmEnvironment,
    SwarmCoordinator,
    EmergentBehavior,
)

from .stigmergy import (
    Pheromone,
    PheromoneField,
    StigmergicMemory,
    DigitalPheromoneSystem,
    StigmergicCoordination,
)

from .ant_colony import (
    Ant,
    AntColony,
    ACOPathfinder,
    ACOOptimizer,
    MaxMinAntSystem,
    AntColonySystem,
)

from .particle_swarm import (
    Particle,
    ParticleSwarm,
    PSOptimizer,
    AdaptivePSO,
    QuantumPSO,
    MultiObjectivePSO,
)

from .collective_intelligence import (
    CollectiveMemory,
    ConsensusEngine,
    DistributedReasoning,
    EmergentKnowledge,
    SwarmWisdom,
)

from .self_organization import (
    CriticalityDetector,
    SelfOrganizingMap,
    AvalancheDynamics,
    EdgeOfChaos,
    EmergentStructure,
)

__all__ = [
    # Core
    'SwarmAgent',
    'SwarmMessage',
    'SwarmEnvironment',
    'SwarmCoordinator',
    'EmergentBehavior',
    # Stigmergy
    'Pheromone',
    'PheromoneField',
    'StigmergicMemory',
    'DigitalPheromoneSystem',
    'StigmergicCoordination',
    # ACO
    'Ant',
    'AntColony',
    'ACOPathfinder',
    'ACOOptimizer',
    'MaxMinAntSystem',
    'AntColonySystem',
    # PSO
    'Particle',
    'ParticleSwarm',
    'PSOptimizer',
    'AdaptivePSO',
    'QuantumPSO',
    'MultiObjectivePSO',
    # Collective Intelligence
    'CollectiveMemory',
    'ConsensusEngine',
    'DistributedReasoning',
    'EmergentKnowledge',
    'SwarmWisdom',
    # Self-Organization
    'CriticalityDetector',
    'SelfOrganizingMap',
    'AvalancheDynamics',
    'EdgeOfChaos',
    'EmergentStructure',
]
