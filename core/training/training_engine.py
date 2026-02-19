"""
BAEL Training Engine
=====================

Core training loop implementation.
Handles model training with full control.

Features:
- Training loop
- Gradient handling
- Metric tracking
- Callback system
- Distributed training
"""

import hashlib
import logging
import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .dataset_manager import DataLoader, Dataset, DataSplit
from .training_config import TrainingConfig

logger = logging.getLogger(__name__)


class TrainingPhase(Enum):
    """Training phases."""
    WARMUP = "warmup"
    TRAINING = "training"
    EVALUATION = "evaluation"
    FINISHED = "finished"


@dataclass
class TrainingMetrics:
    """Training metrics at a point in time."""
    step: int
    epoch: float

    # Loss
    loss: float = 0.0
    val_loss: float = 0.0

    # Additional metrics
    perplexity: float = 0.0
    accuracy: float = 0.0

    # Learning rate
    learning_rate: float = 0.0

    # Performance
    samples_per_second: float = 0.0
    tokens_per_second: float = 0.0

    # Memory
    gpu_memory_mb: float = 0.0

    # Time
    elapsed_seconds: float = 0.0
    eta_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step": self.step,
            "epoch": self.epoch,
            "loss": self.loss,
            "val_loss": self.val_loss,
            "perplexity": self.perplexity,
            "learning_rate": self.learning_rate,
        }


@dataclass
class TrainingResult:
    """Result of training run."""
    run_id: str

    # Status
    success: bool = True
    error: Optional[str] = None

    # Final metrics
    final_loss: float = 0.0
    final_val_loss: float = 0.0
    best_val_loss: float = float('inf')

    # Progress
    total_steps: int = 0
    total_epochs: int = 0

    # Time
    total_time_seconds: float = 0.0

    # Checkpoints
    best_checkpoint: Optional[str] = None
    final_checkpoint: Optional[str] = None

    # History
    metrics_history: List[TrainingMetrics] = field(default_factory=list)


class TrainingCallback:
    """Base class for training callbacks."""

    def on_train_begin(self, config: TrainingConfig) -> None:
        """Called at training start."""
        pass

    def on_train_end(self, result: TrainingResult) -> None:
        """Called at training end."""
        pass

    def on_epoch_begin(self, epoch: int) -> None:
        """Called at epoch start."""
        pass

    def on_epoch_end(self, epoch: int, metrics: TrainingMetrics) -> None:
        """Called at epoch end."""
        pass

    def on_step_begin(self, step: int) -> None:
        """Called at step start."""
        pass

    def on_step_end(self, step: int, metrics: TrainingMetrics) -> None:
        """Called at step end."""
        pass

    def on_evaluate(self, metrics: TrainingMetrics) -> None:
        """Called after evaluation."""
        pass


class PrintCallback(TrainingCallback):
    """Callback that prints progress."""

    def on_step_end(self, step: int, metrics: TrainingMetrics) -> None:
        if step % 10 == 0:
            print(f"Step {step}: loss={metrics.loss:.4f}, lr={metrics.learning_rate:.2e}")

    def on_epoch_end(self, epoch: int, metrics: TrainingMetrics) -> None:
        print(f"Epoch {epoch}: loss={metrics.loss:.4f}, val_loss={metrics.val_loss:.4f}")


class EarlyStoppingCallback(TrainingCallback):
    """Early stopping callback."""

    def __init__(self, patience: int = 3, min_delta: float = 0.0):
        self.patience = patience
        self.min_delta = min_delta
        self.best_loss = float('inf')
        self.counter = 0
        self.should_stop = False

    def on_evaluate(self, metrics: TrainingMetrics) -> None:
        if metrics.val_loss < self.best_loss - self.min_delta:
            self.best_loss = metrics.val_loss
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.should_stop = True
                logger.info(f"Early stopping triggered at step {metrics.step}")


class TrainingEngine:
    """
    Training engine for BAEL.

    Manages the training loop.
    """

    def __init__(
        self,
        config: TrainingConfig,
        model: Optional[Any] = None,  # PyTorch model
        tokenizer: Optional[Any] = None,
    ):
        self.config = config
        self.model = model
        self.tokenizer = tokenizer

        # Callbacks
        self._callbacks: List[TrainingCallback] = []

        # State
        self._current_step = 0
        self._current_epoch = 0
        self._phase = TrainingPhase.WARMUP

        # Metrics
        self._metrics_history: List[TrainingMetrics] = []

        # Stats
        self.stats = {
            "runs_completed": 0,
            "total_steps_trained": 0,
        }

    def add_callback(self, callback: TrainingCallback) -> None:
        """Add a training callback."""
        self._callbacks.append(callback)

    def _emit(self, event: str, *args, **kwargs) -> None:
        """Emit event to callbacks."""
        for callback in self._callbacks:
            handler = getattr(callback, event, None)
            if handler:
                try:
                    handler(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Callback error: {e}")

    def train(
        self,
        train_dataset: Dataset,
        eval_dataset: Optional[Dataset] = None,
    ) -> TrainingResult:
        """
        Run training.

        Args:
            train_dataset: Training dataset
            eval_dataset: Optional evaluation dataset

        Returns:
            Training result
        """
        run_id = hashlib.md5(
            f"{self.config.run_name}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        result = TrainingResult(run_id=run_id)
        start_time = time.time()

        try:
            self._emit("on_train_begin", self.config)

            # Create data loaders
            train_loader = DataLoader(
                train_dataset,
                split=DataSplit.TRAIN,
                batch_size=self.config.hardware.per_device_batch_size,
                shuffle=True,
            )

            eval_loader = None
            if eval_dataset:
                eval_loader = DataLoader(
                    eval_dataset,
                    split=DataSplit.VALIDATION,
                    batch_size=self.config.hardware.per_device_batch_size,
                    shuffle=False,
                )

            # Calculate steps
            steps_per_epoch = len(train_loader)
            total_steps = (
                self.config.max_steps if self.config.max_steps > 0
                else steps_per_epoch * self.config.num_epochs
            )

            # Training loop
            self._current_step = 0
            running_loss = 0.0

            for epoch in range(self.config.num_epochs):
                self._current_epoch = epoch
                self._emit("on_epoch_begin", epoch)

                epoch_loss = 0.0
                epoch_steps = 0

                for batch in train_loader:
                    self._emit("on_step_begin", self._current_step)

                    # Simulate training step
                    loss = self._train_step(batch)

                    epoch_loss += loss
                    running_loss += loss
                    epoch_steps += 1
                    self._current_step += 1

                    # Calculate metrics
                    metrics = TrainingMetrics(
                        step=self._current_step,
                        epoch=epoch + epoch_steps / steps_per_epoch,
                        loss=running_loss / min(self._current_step, 100),
                        learning_rate=self._get_lr(),
                        elapsed_seconds=time.time() - start_time,
                    )

                    if metrics.loss > 0:
                        metrics.perplexity = min(math.exp(metrics.loss), 1e6)

                    self._metrics_history.append(metrics)
                    self._emit("on_step_end", self._current_step, metrics)

                    # Evaluation
                    if (eval_loader and
                        self._current_step % self.config.evaluation.eval_steps == 0):

                        val_loss = self._evaluate(eval_loader)
                        metrics.val_loss = val_loss

                        if val_loss < result.best_val_loss:
                            result.best_val_loss = val_loss

                        self._emit("on_evaluate", metrics)

                        # Check early stopping
                        for callback in self._callbacks:
                            if isinstance(callback, EarlyStoppingCallback):
                                if callback.should_stop:
                                    break

                    if self._current_step >= total_steps:
                        break

                # Epoch end metrics
                epoch_metrics = TrainingMetrics(
                    step=self._current_step,
                    epoch=epoch + 1,
                    loss=epoch_loss / max(epoch_steps, 1),
                    val_loss=result.best_val_loss,
                    elapsed_seconds=time.time() - start_time,
                )

                self._emit("on_epoch_end", epoch, epoch_metrics)

                if self._current_step >= total_steps:
                    break

            # Final result
            result.success = True
            result.total_steps = self._current_step
            result.total_epochs = self._current_epoch + 1
            result.final_loss = running_loss / max(self._current_step, 1)
            result.metrics_history = self._metrics_history

        except Exception as e:
            result.success = False
            result.error = str(e)
            logger.error(f"Training failed: {e}")

        finally:
            result.total_time_seconds = time.time() - start_time
            self._emit("on_train_end", result)

        self.stats["runs_completed"] += 1
        self.stats["total_steps_trained"] += result.total_steps

        return result

    def _train_step(self, batch: List[Any]) -> float:
        """Execute single training step."""
        if self.model is None:
            # Simulate training
            return random.uniform(0.5, 2.0) * (1 - self._current_step / 1000)

        # Actual training would go here
        # self.model.train()
        # outputs = self.model(**batch)
        # loss = outputs.loss
        # loss.backward()
        # optimizer.step()
        # return loss.item()

        return 0.0

    def _evaluate(self, eval_loader: DataLoader) -> float:
        """Run evaluation."""
        if self.model is None:
            # Simulate evaluation
            return random.uniform(0.5, 1.5)

        # Actual evaluation would go here
        total_loss = 0.0
        total_steps = 0

        # self.model.eval()
        # with torch.no_grad():
        #     for batch in eval_loader:
        #         outputs = self.model(**batch)
        #         total_loss += outputs.loss.item()
        #         total_steps += 1

        return total_loss / max(total_steps, 1)

    def _get_lr(self) -> float:
        """Get current learning rate."""
        base_lr = self.config.optimizer.learning_rate
        warmup_steps = self.config.scheduler.warmup_steps

        if self._current_step < warmup_steps:
            return base_lr * (self._current_step / max(warmup_steps, 1))

        return base_lr

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            **self.stats,
            "current_step": self._current_step,
            "current_epoch": self._current_epoch,
            "phase": self._phase.value,
        }


def demo():
    """Demonstrate training engine."""
    print("=" * 60)
    print("BAEL Training Engine Demo")
    print("=" * 60)

    from .dataset_manager import DatasetManager

    # Create config
    config = TrainingConfig(
        run_name="demo_training",
        num_epochs=2,
        hardware=HardwareConfig(
            per_device_batch_size=4,
        ),
        evaluation=EvaluationConfig(
            eval_steps=10,
        ),
    )

    print(f"\n{config.summary()}")

    # Create dataset
    manager = DatasetManager()

    samples = [
        {"input": f"Question {i}", "target": f"Answer {i}"}
        for i in range(100)
    ]

    dataset = manager.create_dataset("demo", samples)

    print(f"\nDataset: {len(dataset)} samples")

    # Create engine
    engine = TrainingEngine(config)

    # Add callbacks
    engine.add_callback(PrintCallback())

    early_stopping = EarlyStoppingCallback(patience=3)
    engine.add_callback(early_stopping)

    # Train
    print("\nStarting training...")
    result = engine.train(dataset, dataset)

    print(f"\n{'=' * 50}")
    print(f"Training Complete!")
    print(f"  Success: {result.success}")
    print(f"  Steps: {result.total_steps}")
    print(f"  Epochs: {result.total_epochs}")
    print(f"  Final loss: {result.final_loss:.4f}")
    print(f"  Best val loss: {result.best_val_loss:.4f}")
    print(f"  Time: {result.total_time_seconds:.2f}s")

    print(f"\nStats: {engine.get_stats()}")


# Import for type hints
from .training_config import EvaluationConfig, HardwareConfig

if __name__ == "__main__":
    demo()
