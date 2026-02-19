"""
⚡ META-COGNITIVE ORACLE ⚡
==========================
Self-aware reasoning about own capabilities and limitations.

This module implements genuine metacognition:
- Self-model maintenance
- Capability assessment
- Uncertainty quantification
- Strategy selection
- Learning from introspection
"""

from .meta_core import (
    SelfModel,
    CapabilityProfile,
    CognitiveState,
    IntrospectionEngine,
    MetaCognition,
)

from .uncertainty import (
    UncertaintyType,
    UncertaintyEstimate,
    AleatoricUncertainty,
    EpistemicUncertainty,
    UncertaintyQuantifier,
    ConfidenceCalibrator,
)

from .strategy_selection import (
    Strategy,
    StrategyLibrary,
    PerformanceTracker,
    StrategySelector,
    AdaptiveStrategist,
)

from .self_improvement import (
    LearningOpportunity,
    SkillGap,
    ImprovementPlan,
    SelfImprover,
    MetaLearner,
)

from .cognitive_monitoring import (
    CognitiveLoad,
    AttentionMonitor,
    MemoryMonitor,
    ReasoningMonitor,
    CognitiveResourceManager,
)

__all__ = [
    # Core
    'SelfModel',
    'CapabilityProfile',
    'CognitiveState',
    'IntrospectionEngine',
    'MetaCognition',
    # Uncertainty
    'UncertaintyType',
    'UncertaintyEstimate',
    'AleatoricUncertainty',
    'EpistemicUncertainty',
    'UncertaintyQuantifier',
    'ConfidenceCalibrator',
    # Strategy
    'Strategy',
    'StrategyLibrary',
    'PerformanceTracker',
    'StrategySelector',
    'AdaptiveStrategist',
    # Self-Improvement
    'LearningOpportunity',
    'SkillGap',
    'ImprovementPlan',
    'SelfImprover',
    'MetaLearner',
    # Monitoring
    'CognitiveLoad',
    'AttentionMonitor',
    'MemoryMonitor',
    'ReasoningMonitor',
    'CognitiveResourceManager',
]
