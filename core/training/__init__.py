"""
BAEL Model Training Pipeline
=============================

End-to-end training infrastructure for AI models.
Supports fine-tuning, LoRA, and custom training.

Components:
- DatasetManager: Dataset handling and preprocessing
- TrainingConfig: Training configuration
- TrainingEngine: Core training loop
- LoRAAdapter: Low-rank adaptation
- ModelOptimizer: Hyperparameter optimization
- CheckpointManager: Model checkpointing
"""

from .checkpoint_manager import (CheckpointConfig, CheckpointManager,
                                 CheckpointStrategy, ModelCheckpoint)
from .dataset_manager import (DataLoader, Dataset, DatasetManager, DataSplit,
                              Preprocessor)
from .hyperparameter_optimizer import (HyperparameterOptimizer,
                                       OptimizationResult, SearchSpace, Trial)
from .lora_adapter import LoRAAdapter, LoRAConfig, LoRAInjector, LoRALayer
from .training_config import (HardwareConfig, OptimizerConfig, SchedulerConfig,
                              TrainingConfig)
from .training_engine import (TrainingCallback, TrainingEngine,
                              TrainingMetrics, TrainingResult)

__all__ = [
    # Dataset
    "DatasetManager",
    "Dataset",
    "DataSplit",
    "DataLoader",
    "Preprocessor",
    # Config
    "TrainingConfig",
    "OptimizerConfig",
    "SchedulerConfig",
    "HardwareConfig",
    # Training
    "TrainingEngine",
    "TrainingResult",
    "TrainingMetrics",
    "TrainingCallback",
    # LoRA
    "LoRAAdapter",
    "LoRAConfig",
    "LoRALayer",
    "LoRAInjector",
    # Hyperparameter
    "HyperparameterOptimizer",
    "SearchSpace",
    "Trial",
    "OptimizationResult",
    # Checkpoint
    "CheckpointManager",
    "ModelCheckpoint",
    "CheckpointConfig",
    "CheckpointStrategy",
]
