"""
BAEL Evolution Package

Self-improvement through evolutionary algorithms:
- Genetic Algorithm optimization
- NSGA-II multi-objective optimization
- Neuroevolution
- Capability evolution
"""

from .self_evolution import (NSGA2, CapabilityFitness, CrossoverType,
                             EvolutionConfig, EvolutionStats,
                             EvolutionStrategy, FitnessFunction,
                             GeneticOperators, Individual, MutationType,
                             SelectionMethod, SelfEvolutionEngine)

__all__ = [
    "SelfEvolutionEngine",
    "EvolutionConfig",
    "EvolutionStrategy",
    "Individual",
    "EvolutionStats",
    "CapabilityFitness",
    "FitnessFunction",
    "GeneticOperators",
    "NSGA2",
    "SelectionMethod",
    "MutationType",
    "CrossoverType"
]
