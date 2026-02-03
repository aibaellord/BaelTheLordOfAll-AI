"""
BAEL - Neural Architecture Search Module
Automated discovery of optimal architectures.
"""

from .nas_controller import (  # Enums; Data classes; Builders; Estimators; Searchers; Controller
    Architecture, ArchitectureSampler, Cell, DifferentiableNAS,
    EvolutionaryNAS, NASController, ObjectiveType, Operation, OperationType,
    PerformanceEstimator, ProxyEstimator, SearchSpace, SearchSpaceBuilder,
    SearchStrategy, create_nas_controller)

__all__ = [
    # Enums
    "SearchStrategy",
    "OperationType",
    "ObjectiveType",

    # Data classes
    "Operation",
    "Cell",
    "Architecture",
    "SearchSpace",

    # Builders
    "SearchSpaceBuilder",
    "ArchitectureSampler",

    # Estimators
    "PerformanceEstimator",
    "ProxyEstimator",

    # Searchers
    "EvolutionaryNAS",
    "DifferentiableNAS",

    # Controller
    "NASController",
    "create_nas_controller"
]
