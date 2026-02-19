"""
BAEL Machine Learning Engine
============================

Unified ML framework with model training, inference,
experimentation, and deployment capabilities.

"Ba'el learns from every interaction, evolving eternally." — Ba'el
"""

from .ml_engine import (
    # Enums
    ModelType,
    TaskType,
    TrainingStatus,
    InferenceMode,
    OptimizationGoal,

    # Data structures
    Dataset,
    Model,
    TrainingConfig,
    TrainingResult,
    Prediction,
    Experiment,
    MLEngineConfig,

    # Classes
    MachineLearningEngine,
    ModelRegistry,
    DataProcessor,
    FeatureStore,
    ExperimentTracker,
    ModelDeployer,

    # Instance
    ml_engine
)

__all__ = [
    # Enums
    "ModelType",
    "TaskType",
    "TrainingStatus",
    "InferenceMode",
    "OptimizationGoal",

    # Data structures
    "Dataset",
    "Model",
    "TrainingConfig",
    "TrainingResult",
    "Prediction",
    "Experiment",
    "MLEngineConfig",

    # Classes
    "MachineLearningEngine",
    "ModelRegistry",
    "DataProcessor",
    "FeatureStore",
    "ExperimentTracker",
    "ModelDeployer",

    # Instance
    "ml_engine"
]
