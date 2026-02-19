"""
BAEL Training Configuration
============================

Configuration management for model training.
Defines all training hyperparameters.

Features:
- Training hyperparameters
- Optimizer configuration
- Scheduler configuration
- Hardware settings
- Validation settings
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class OptimizerType(Enum):
    """Supported optimizers."""
    ADAM = "adam"
    ADAMW = "adamw"
    SGD = "sgd"
    ADAFACTOR = "adafactor"
    LION = "lion"
    SOPHIA = "sophia"


class SchedulerType(Enum):
    """Learning rate schedulers."""
    CONSTANT = "constant"
    LINEAR = "linear"
    COSINE = "cosine"
    COSINE_WITH_RESTARTS = "cosine_with_restarts"
    POLYNOMIAL = "polynomial"
    WARMUP_STABLE_DECAY = "warmup_stable_decay"


class PrecisionType(Enum):
    """Training precision."""
    FP32 = "fp32"
    FP16 = "fp16"
    BF16 = "bf16"
    FP8 = "fp8"


class GradientAccumulationType(Enum):
    """Gradient accumulation strategies."""
    NONE = "none"
    FIXED = "fixed"
    DYNAMIC = "dynamic"


@dataclass
class OptimizerConfig:
    """Optimizer configuration."""
    type: OptimizerType = OptimizerType.ADAMW

    # Learning rate
    learning_rate: float = 1e-5
    weight_decay: float = 0.01

    # Adam specific
    beta1: float = 0.9
    beta2: float = 0.999
    epsilon: float = 1e-8

    # SGD specific
    momentum: float = 0.9
    nesterov: bool = False

    # Gradient clipping
    max_grad_norm: float = 1.0
    clip_by_value: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type.value,
            "learning_rate": self.learning_rate,
            "weight_decay": self.weight_decay,
            "betas": (self.beta1, self.beta2),
            "eps": self.epsilon,
            "max_grad_norm": self.max_grad_norm,
        }


@dataclass
class SchedulerConfig:
    """Learning rate scheduler configuration."""
    type: SchedulerType = SchedulerType.COSINE

    # Warmup
    warmup_steps: int = 100
    warmup_ratio: float = 0.0  # Alternative to steps

    # Decay
    num_training_steps: int = 0  # Set during training
    min_lr_ratio: float = 0.0  # Final LR = initial * min_lr_ratio

    # Cosine restarts
    num_cycles: int = 1

    # Polynomial
    power: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type.value,
            "warmup_steps": self.warmup_steps,
            "num_training_steps": self.num_training_steps,
        }


@dataclass
class HardwareConfig:
    """Hardware configuration."""
    # Device
    device: str = "auto"  # "cpu", "cuda", "mps", "auto"

    # Precision
    precision: PrecisionType = PrecisionType.FP16

    # Multi-GPU
    num_gpus: int = 1
    distributed: bool = False

    # Memory optimization
    gradient_checkpointing: bool = False
    cpu_offload: bool = False

    # Batch size
    per_device_batch_size: int = 8
    gradient_accumulation_steps: int = 1

    @property
    def effective_batch_size(self) -> int:
        """Calculate effective batch size."""
        return (
            self.per_device_batch_size *
            self.gradient_accumulation_steps *
            self.num_gpus
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "device": self.device,
            "precision": self.precision.value,
            "num_gpus": self.num_gpus,
            "effective_batch_size": self.effective_batch_size,
        }


@dataclass
class EvaluationConfig:
    """Evaluation configuration."""
    # Frequency
    eval_steps: int = 500
    eval_strategy: str = "steps"  # "steps", "epoch"

    # Metrics
    metrics: List[str] = field(default_factory=lambda: ["loss", "perplexity"])

    # Early stopping
    early_stopping: bool = False
    early_stopping_patience: int = 3
    early_stopping_threshold: float = 0.0

    # Generation evaluation
    generate_during_eval: bool = False
    max_new_tokens: int = 128

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "eval_steps": self.eval_steps,
            "eval_strategy": self.eval_strategy,
            "metrics": self.metrics,
            "early_stopping": self.early_stopping,
        }


@dataclass
class LoggingConfig:
    """Logging configuration."""
    # Logging frequency
    log_steps: int = 10
    log_level: str = "info"

    # Outputs
    log_to_console: bool = True
    log_to_file: bool = True
    log_file: str = "./logs/training.log"

    # Integrations
    use_wandb: bool = False
    wandb_project: str = "bael-training"
    wandb_run_name: Optional[str] = None

    use_tensorboard: bool = True
    tensorboard_dir: str = "./logs/tensorboard"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "log_steps": self.log_steps,
            "use_wandb": self.use_wandb,
            "use_tensorboard": self.use_tensorboard,
        }


@dataclass
class TrainingConfig:
    """Complete training configuration."""
    # Run identification
    run_name: str = "bael_training"
    output_dir: str = "./outputs"

    # Training duration
    num_epochs: int = 3
    max_steps: int = -1  # -1 = use epochs

    # Data
    max_seq_length: int = 512

    # Sub-configs
    optimizer: OptimizerConfig = field(default_factory=OptimizerConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    hardware: HardwareConfig = field(default_factory=HardwareConfig)
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # Checkpointing
    save_steps: int = 500
    save_total_limit: int = 3
    save_on_each_epoch: bool = True
    resume_from_checkpoint: Optional[str] = None

    # Reproducibility
    seed: int = 42

    # Advanced
    dataloader_num_workers: int = 4
    dataloader_pin_memory: bool = True

    def validate(self) -> List[str]:
        """Validate configuration."""
        errors = []

        if self.optimizer.learning_rate <= 0:
            errors.append("Learning rate must be positive")

        if self.num_epochs <= 0 and self.max_steps <= 0:
            errors.append("Must specify epochs or max_steps")

        if self.hardware.per_device_batch_size <= 0:
            errors.append("Batch size must be positive")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "run_name": self.run_name,
            "output_dir": self.output_dir,
            "num_epochs": self.num_epochs,
            "max_steps": self.max_steps,
            "max_seq_length": self.max_seq_length,
            "optimizer": self.optimizer.to_dict(),
            "scheduler": self.scheduler.to_dict(),
            "hardware": self.hardware.to_dict(),
            "evaluation": self.evaluation.to_dict(),
            "logging": self.logging.to_dict(),
            "seed": self.seed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrainingConfig":
        """Create from dictionary."""
        config = cls(
            run_name=data.get("run_name", "bael_training"),
            output_dir=data.get("output_dir", "./outputs"),
            num_epochs=data.get("num_epochs", 3),
            max_steps=data.get("max_steps", -1),
            max_seq_length=data.get("max_seq_length", 512),
            seed=data.get("seed", 42),
        )

        if "optimizer" in data:
            opt = data["optimizer"]
            config.optimizer.learning_rate = opt.get("learning_rate", 1e-5)
            config.optimizer.weight_decay = opt.get("weight_decay", 0.01)

        return config

    def summary(self) -> str:
        """Get configuration summary."""
        lines = [
            f"Training Configuration: {self.run_name}",
            "=" * 50,
            f"Epochs: {self.num_epochs}",
            f"Max steps: {self.max_steps}",
            f"Sequence length: {self.max_seq_length}",
            "",
            "Optimizer:",
            f"  Type: {self.optimizer.type.value}",
            f"  Learning rate: {self.optimizer.learning_rate}",
            f"  Weight decay: {self.optimizer.weight_decay}",
            "",
            "Hardware:",
            f"  Precision: {self.hardware.precision.value}",
            f"  Batch size: {self.hardware.per_device_batch_size}",
            f"  Gradient accumulation: {self.hardware.gradient_accumulation_steps}",
            f"  Effective batch: {self.hardware.effective_batch_size}",
            "",
            "Evaluation:",
            f"  Eval steps: {self.evaluation.eval_steps}",
            f"  Early stopping: {self.evaluation.early_stopping}",
        ]
        return "\n".join(lines)


# Preset configurations
class TrainingPresets:
    """Preset training configurations."""

    @staticmethod
    def small_model() -> TrainingConfig:
        """Config for small models (<1B)."""
        return TrainingConfig(
            run_name="small_model",
            optimizer=OptimizerConfig(learning_rate=5e-5),
            hardware=HardwareConfig(
                per_device_batch_size=16,
                precision=PrecisionType.FP16,
            ),
        )

    @staticmethod
    def medium_model() -> TrainingConfig:
        """Config for medium models (1-10B)."""
        return TrainingConfig(
            run_name="medium_model",
            optimizer=OptimizerConfig(learning_rate=2e-5),
            hardware=HardwareConfig(
                per_device_batch_size=4,
                gradient_accumulation_steps=4,
                precision=PrecisionType.BF16,
                gradient_checkpointing=True,
            ),
        )

    @staticmethod
    def large_model() -> TrainingConfig:
        """Config for large models (10B+)."""
        return TrainingConfig(
            run_name="large_model",
            optimizer=OptimizerConfig(learning_rate=1e-5),
            hardware=HardwareConfig(
                per_device_batch_size=1,
                gradient_accumulation_steps=16,
                precision=PrecisionType.BF16,
                gradient_checkpointing=True,
                cpu_offload=True,
            ),
        )

    @staticmethod
    def lora_finetuning() -> TrainingConfig:
        """Config for LoRA fine-tuning."""
        return TrainingConfig(
            run_name="lora_finetune",
            num_epochs=1,
            optimizer=OptimizerConfig(
                learning_rate=1e-4,
                weight_decay=0.0,
            ),
            hardware=HardwareConfig(
                per_device_batch_size=4,
                precision=PrecisionType.FP16,
            ),
            evaluation=EvaluationConfig(
                eval_steps=100,
            ),
        )


def demo():
    """Demonstrate training configuration."""
    print("=" * 60)
    print("BAEL Training Configuration Demo")
    print("=" * 60)

    # Default config
    print("\nDefault configuration:")
    config = TrainingConfig()
    print(config.summary())

    # Validate
    errors = config.validate()
    print(f"\nValidation: {'✓ Valid' if not errors else '✗ ' + str(errors)}")

    # Presets
    print("\n" + "=" * 50)
    print("Preset configurations:")

    for preset_name in ["small_model", "medium_model", "large_model", "lora_finetuning"]:
        preset = getattr(TrainingPresets, preset_name)()
        print(f"\n{preset_name}:")
        print(f"  LR: {preset.optimizer.learning_rate}")
        print(f"  Batch: {preset.hardware.effective_batch_size}")
        print(f"  Precision: {preset.hardware.precision.value}")

    # Serialization
    print("\n" + "=" * 50)
    print("Serialization:")

    config_dict = config.to_dict()
    print(f"  Keys: {list(config_dict.keys())}")

    restored = TrainingConfig.from_dict(config_dict)
    print(f"  Restored run_name: {restored.run_name}")


if __name__ == "__main__":
    demo()
