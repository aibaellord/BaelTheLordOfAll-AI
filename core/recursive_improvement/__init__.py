"""
🔄 RECURSIVE SELF-IMPROVEMENT CORE 🔄
======================================
Self-modifying intelligence.

Features:
- Capability assessment
- Improvement planning
- Self-modification
- Version control
"""

from .improvement_core import (
    Capability,
    CapabilityLevel,
    CapabilityAssessment,
    PerformanceMetric,
    ImprovementGoal,
    SelfAssessor,
)

from .modification_engine import (
    ModificationType,
    Modification,
    ModificationPlan,
    ModificationEngine,
    SafetyValidator,
)

from .learning_system import (
    Experience,
    LearningStrategy,
    KnowledgeUpdate,
    ContinuousLearner,
    TransferLearning,
)

from .version_control import (
    Version,
    ChangeLog,
    VersionManager,
    RollbackManager,
    CapabilitySnapshot,
)

from .meta_optimizer import (
    OptimizationStrategy,
    MetaParameter,
    HyperparameterTuner,
    ArchitectureSearcher,
    MetaOptimizer,
)

__all__ = [
    # Improvement Core
    'Capability',
    'CapabilityLevel',
    'CapabilityAssessment',
    'PerformanceMetric',
    'ImprovementGoal',
    'SelfAssessor',

    # Modification Engine
    'ModificationType',
    'Modification',
    'ModificationPlan',
    'ModificationEngine',
    'SafetyValidator',

    # Learning System
    'Experience',
    'LearningStrategy',
    'KnowledgeUpdate',
    'ContinuousLearner',
    'TransferLearning',

    # Version Control
    'Version',
    'ChangeLog',
    'VersionManager',
    'RollbackManager',
    'CapabilitySnapshot',

    # Meta Optimizer
    'OptimizationStrategy',
    'MetaParameter',
    'HyperparameterTuner',
    'ArchitectureSearcher',
    'MetaOptimizer',
]
