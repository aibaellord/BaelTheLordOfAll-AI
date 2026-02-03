"""
BAEL Continual Learning Module

This module implements advanced continual learning capabilities
to enable BAEL to learn continuously without catastrophic forgetting.

Key Components:
- Elastic Weight Consolidation (EWC)
- PackNet for parameter isolation
- Experience Replay buffers
- Progressive Neural Networks concepts
- Memory-Aware Synapses

Together these enable true lifelong learning.
"""

from .continual_learner import (ContinualLearner, LearningSession,
                                LearningStrategy, LearningTask)
from .ewc import ElasticWeightConsolidation, FisherMatrix
from .knowledge_distillation import KnowledgeDistiller
from .packnet import NetworkMask, PackNet
from .replay_buffer import ExperienceReplayBuffer, PrioritizedReplayBuffer

__all__ = [
    "ContinualLearner",
    "LearningSession",
    "LearningTask",
    "LearningStrategy",
    "ElasticWeightConsolidation",
    "FisherMatrix",
    "PackNet",
    "NetworkMask",
    "ExperienceReplayBuffer",
    "PrioritizedReplayBuffer",
    "KnowledgeDistiller",
]
