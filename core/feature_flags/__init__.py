"""
BAEL Feature Flags Engine
=========================

Feature flags and A/B testing with:
- Boolean flags
- Percentage rollouts
- User targeting
- A/B testing
- Analytics

"Ba'el controls which realities manifest." — Ba'el
"""

from .feature_flags_engine import (
    # Enums
    FlagType,
    RolloutType,
    TargetType,
    VariantType,

    # Data structures
    Flag,
    Variant,
    Rollout,
    Target,
    Experiment,
    FeatureFlagsConfig,

    # Classes
    FeatureFlagsEngine,
    FlagEvaluator,
    TargetingEngine,
    ExperimentManager,

    # Instance
    feature_flags_engine
)

__all__ = [
    'FlagType',
    'RolloutType',
    'TargetType',
    'VariantType',
    'Flag',
    'Variant',
    'Rollout',
    'Target',
    'Experiment',
    'FeatureFlagsConfig',
    'FeatureFlagsEngine',
    'FlagEvaluator',
    'TargetingEngine',
    'ExperimentManager',
    'feature_flags_engine'
]
