"""
BAEL Meta-Learning Package

Learning-to-learn capabilities for rapid task adaptation:
- MAML (Model-Agnostic Meta-Learning)
- Reptile
- Prototypical Networks
- Meta-SGD
"""

from .meta_framework import (MAMLLearner, MetaGradient, MetaLearningConfig,
                             MetaLearningFramework, MetaLearningStrategy,
                             PrototypicalNetwork, ReptileLearner,
                             TaskDistribution, TaskExperience, TaskType)

__all__ = [
    "MetaLearningFramework",
    "MetaLearningConfig",
    "MetaLearningStrategy",
    "TaskType",
    "TaskDistribution",
    "TaskExperience",
    "MAMLLearner",
    "ReptileLearner",
    "PrototypicalNetwork",
    "MetaGradient"
]
