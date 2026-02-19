"""
BAEL Maximum Power Package
===========================

Ultimate optimization and intelligence capabilities.

"At maximum power, the impossible becomes routine." — Ba'el
"""

from .quantum_optimizer import (
    QuantumOptimizer,
    QuantumAnnealer,
    GroverSearch,
    QAOA,
    QuantumWalk,
    QuantumState,
    OptimizationAlgorithm,
    Qubit,
    QuantumRegister,
    Solution,
    OptimizationResult,
    quantum_optimizer,
)

from .neural_architecture_search import (
    NeuralArchitectureSearch,
    EvolutionaryNAS,
    AgingEvolutionNAS,
    ArchitectureGenerator,
    LayerType,
    ActivationType,
    SearchStrategy,
    TaskType,
    LayerConfig,
    Architecture,
    SearchSpace,
    SearchResult,
    nas,
)

from .swarm_coordinator import (
    SwarmCoordinator,
    ParticleSwarmOptimization,
    AntColonyOptimization,
    BeeAlgorithm,
    SwarmAlgorithm,
    AgentRole,
    CommunicationType,
    Position,
    SwarmAgent,
    Pheromone,
    SwarmState,
    SwarmResult,
    swarm,
)

from .meta_learning import (
    MetaLearningSystem,
    PrototypicalLearner,
    MAMLLearner,
    CurriculumLearner,
    ExperienceBuffer,
    LearningStrategy,
    AdaptationSpeed,
    Task,
    LearningExperience,
    MetaKnowledge,
    Prototype,
    AdaptationResult,
    meta_learner,
)

__all__ = [
    # Quantum Optimization
    "QuantumOptimizer",
    "QuantumAnnealer",
    "GroverSearch",
    "QAOA",
    "QuantumWalk",
    "QuantumState",
    "OptimizationAlgorithm",
    "Qubit",
    "QuantumRegister",
    "Solution",
    "OptimizationResult",
    "quantum_optimizer",
    # Neural Architecture Search
    "NeuralArchitectureSearch",
    "EvolutionaryNAS",
    "AgingEvolutionNAS",
    "ArchitectureGenerator",
    "LayerType",
    "ActivationType",
    "SearchStrategy",
    "TaskType",
    "LayerConfig",
    "Architecture",
    "SearchSpace",
    "SearchResult",
    "nas",
    # Swarm Intelligence
    "SwarmCoordinator",
    "ParticleSwarmOptimization",
    "AntColonyOptimization",
    "BeeAlgorithm",
    "SwarmAlgorithm",
    "AgentRole",
    "CommunicationType",
    "Position",
    "SwarmAgent",
    "Pheromone",
    "SwarmState",
    "SwarmResult",
    "swarm",
    # Meta-Learning
    "MetaLearningSystem",
    "PrototypicalLearner",
    "MAMLLearner",
    "CurriculumLearner",
    "ExperienceBuffer",
    "LearningStrategy",
    "AdaptationSpeed",
    "Task",
    "LearningExperience",
    "MetaKnowledge",
    "Prototype",
    "AdaptationResult",
    "meta_learner",
]
