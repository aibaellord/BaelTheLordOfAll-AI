"""
⚡ AUTONOMOUS EVOLUTION SYSTEM ⚡
================================
Self-evolving agent capabilities.

Features:
- Genetic algorithms
- Evolution strategies
- Fitness landscapes
- Self-adaptation
"""

from .evolution_core import (
    Gene,
    Chromosome,
    Genome,
    Individual,
    Population,
    EvolutionEngine,
)

from .genetic_algorithms import (
    SelectionMethod,
    CrossoverMethod,
    MutationMethod,
    GeneticAlgorithm,
    NSGA2,
    DifferentialEvolution,
)

from .fitness_landscape import (
    FitnessFunction,
    MultiObjectiveFitness,
    FitnessLandscape,
    LandscapeAnalyzer,
    NKLandscape,
)

from .evolutionary_optimization import (
    EvolutionStrategy,
    CMAEvolutionStrategy,
    NaturalEvolutionStrategy,
    CoevolutionEngine,
    SelfAdaptingEvolver,
)

__all__ = [
    # Evolution Core
    'Gene',
    'Chromosome',
    'Genome',
    'Individual',
    'Population',
    'EvolutionEngine',

    # Genetic Algorithms
    'SelectionMethod',
    'CrossoverMethod',
    'MutationMethod',
    'GeneticAlgorithm',
    'NSGA2',
    'DifferentialEvolution',

    # Fitness Landscape
    'FitnessFunction',
    'MultiObjectiveFitness',
    'FitnessLandscape',
    'LandscapeAnalyzer',
    'NKLandscape',

    # Evolutionary Optimization
    'EvolutionStrategy',
    'CMAEvolutionStrategy',
    'NaturalEvolutionStrategy',
    'CoevolutionEngine',
    'SelfAdaptingEvolver',
]
