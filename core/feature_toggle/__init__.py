"""
BAEL Feature Toggle Engine
==========================

Advanced feature flags with A/B testing and gradual rollouts.

"Ba'el controls reality with the flip of a switch." — Ba'el
"""

from .feature_toggle_engine import (
    # Enums
    FeatureState,
    RolloutStrategy,
    TargetType,

    # Data structures
    FeatureFlag,
    RolloutConfig,
    UserContext,
    FeatureEvaluation,

    # Engine
    FeatureToggleEngine,

    # Convenience
    features,
    is_enabled,
    get_variant,
)

__all__ = [
    'FeatureState',
    'RolloutStrategy',
    'TargetType',
    'FeatureFlag',
    'RolloutConfig',
    'UserContext',
    'FeatureEvaluation',
    'FeatureToggleEngine',
    'features',
    'is_enabled',
    'get_variant',
]
