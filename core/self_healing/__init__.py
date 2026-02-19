"""
BAEL Self-Healing & Automation Package
======================================

Autonomous self-healing, auto-scaling, and continuous improvement.

"The system that heals itself is truly immortal." — Ba'el
"""

from .self_healing_system import (
    SelfHealingSystem,
    ErrorSeverity,
    ErrorCategory,
    RecoveryAction,
    HealthStatus,
    ErrorPattern,
    ErrorOccurrence,
    RecoveryResult,
    HealthReport,
    self_healing,
    get_healing_system,
)

from .auto_scaler import (
    AutoScaler,
    ScalingDirection,
    ScalingStrategy,
    ResourceType,
    LoadLevel,
    ResourceConfig,
    LoadMetrics,
    ScalingDecision,
    ScalingEvent,
    MetricsCollector,
    LoadPredictor,
    get_auto_scaler,
    configure_default_scaling,
)

from .continuous_improvement import (
    ContinuousImprovementEngine,
    ImprovementType,
    LearningSource,
    OptimizationType,
    Observation,
    Insight,
    Improvement,
    ABTest,
    PatternRecognizer,
    ParameterTuner,
    observe,
    get_improvement_engine,
)

__all__ = [
    # Self-Healing
    "SelfHealingSystem",
    "ErrorSeverity",
    "ErrorCategory",
    "RecoveryAction",
    "HealthStatus",
    "ErrorPattern",
    "ErrorOccurrence",
    "RecoveryResult",
    "HealthReport",
    "self_healing",
    "get_healing_system",
    # Auto-Scaler
    "AutoScaler",
    "ScalingDirection",
    "ScalingStrategy",
    "ResourceType",
    "LoadLevel",
    "ResourceConfig",
    "LoadMetrics",
    "ScalingDecision",
    "ScalingEvent",
    "MetricsCollector",
    "LoadPredictor",
    "get_auto_scaler",
    "configure_default_scaling",
    # Continuous Improvement
    "ContinuousImprovementEngine",
    "ImprovementType",
    "LearningSource",
    "OptimizationType",
    "Observation",
    "Insight",
    "Improvement",
    "ABTest",
    "PatternRecognizer",
    "ParameterTuner",
    "observe",
    "get_improvement_engine",
]
