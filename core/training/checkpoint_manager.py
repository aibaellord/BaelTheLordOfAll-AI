"""
BAEL Checkpoint Manager
========================

Model checkpointing and version control.
Manages model saves during training.

Features:
- Checkpoint saving/loading
- Best model tracking
- Checkpoint pruning
- Recovery from failures
- Version control
"""

import hashlib
import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class CheckpointStrategy(Enum):
    """Strategies for when to checkpoint."""
    STEPS = "steps"  # Every N steps
    EPOCH = "epoch"  # End of each epoch
    BEST = "best"  # Only when metric improves
    TIME = "time"  # Every N minutes
    ALL = "all"  # All of the above


@dataclass
class CheckpointConfig:
    """Configuration for checkpointing."""
    # Output
    checkpoint_dir: str = "./checkpoints"

    # Strategy
    strategy: CheckpointStrategy = CheckpointStrategy.STEPS

    # Frequency
    save_steps: int = 500
    save_minutes: float = 30.0

    # Retention
    save_total_limit: int = 3
    keep_best: bool = True
    keep_last: bool = True

    # Format
    save_format: str = "pytorch"  # "pytorch", "safetensors", "both"

    # Optimization
    save_optimizer_state: bool = True
    save_scheduler_state: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "checkpoint_dir": self.checkpoint_dir,
            "strategy": self.strategy.value,
            "save_steps": self.save_steps,
            "save_total_limit": self.save_total_limit,
        }


@dataclass
class ModelCheckpoint:
    """A single model checkpoint."""
    id: str
    path: str

    # Training state
    step: int = 0
    epoch: int = 0

    # Metrics
    metric_value: Optional[float] = None
    metric_name: str = "loss"
    is_best: bool = False

    # Model info
    model_size_mb: float = 0.0

    # Timing
    created_at: datetime = field(default_factory=datetime.now)

    # Files
    files: List[str] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "path": self.path,
            "step": self.step,
            "epoch": self.epoch,
            "metric_value": self.metric_value,
            "is_best": self.is_best,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelCheckpoint":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            path=data["path"],
            step=data.get("step", 0),
            epoch=data.get("epoch", 0),
            metric_value=data.get("metric_value"),
            is_best=data.get("is_best", False),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
        )


class CheckpointManager:
    """
    Checkpoint manager for BAEL training.

    Handles model saving and loading.
    """

    CHECKPOINT_PREFIX = "checkpoint"
    METADATA_FILE = "checkpoint_metadata.json"

    def __init__(
        self,
        config: Optional[CheckpointConfig] = None,
    ):
        self.config = config or CheckpointConfig()

        # Create directory
        self.checkpoint_dir = Path(self.config.checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Checkpoints
        self._checkpoints: List[ModelCheckpoint] = []
        self._best_checkpoint: Optional[ModelCheckpoint] = None
        self._last_checkpoint: Optional[ModelCheckpoint] = None

        # Timing
        self._last_save_time = datetime.now()

        # Stats
        self.stats = {
            "checkpoints_saved": 0,
            "checkpoints_deleted": 0,
            "total_size_mb": 0.0,
        }

        # Load existing checkpoints
        self._load_existing()

    def _load_existing(self) -> None:
        """Load existing checkpoint metadata."""
        metadata_path = self.checkpoint_dir / self.METADATA_FILE

        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                data = json.load(f)

            for ckpt_data in data.get("checkpoints", []):
                ckpt = ModelCheckpoint.from_dict(ckpt_data)
                self._checkpoints.append(ckpt)

                if ckpt.is_best:
                    self._best_checkpoint = ckpt

            if self._checkpoints:
                self._last_checkpoint = self._checkpoints[-1]

    def _save_metadata(self) -> None:
        """Save checkpoint metadata."""
        metadata_path = self.checkpoint_dir / self.METADATA_FILE

        data = {
            "checkpoints": [ckpt.to_dict() for ckpt in self._checkpoints],
            "best_checkpoint_id": self._best_checkpoint.id if self._best_checkpoint else None,
            "updated_at": datetime.now().isoformat(),
        }

        with open(metadata_path, 'w') as f:
            json.dump(data, f, indent=2)

    def should_save(
        self,
        step: int,
        epoch: int,
        metric_value: Optional[float] = None,
    ) -> bool:
        """
        Check if should save checkpoint.

        Args:
            step: Current training step
            epoch: Current epoch
            metric_value: Current metric value

        Returns:
            Whether to save
        """
        strategy = self.config.strategy

        if strategy == CheckpointStrategy.STEPS:
            return step > 0 and step % self.config.save_steps == 0

        elif strategy == CheckpointStrategy.EPOCH:
            # Called at epoch boundary
            return True

        elif strategy == CheckpointStrategy.BEST:
            if metric_value is None:
                return False
            if self._best_checkpoint is None:
                return True
            return metric_value < (self._best_checkpoint.metric_value or float('inf'))

        elif strategy == CheckpointStrategy.TIME:
            elapsed = (datetime.now() - self._last_save_time).total_seconds()
            return elapsed >= self.config.save_minutes * 60

        elif strategy == CheckpointStrategy.ALL:
            # Check all conditions
            return (
                (step > 0 and step % self.config.save_steps == 0) or
                (metric_value is not None and
                 (self._best_checkpoint is None or
                  metric_value < (self._best_checkpoint.metric_value or float('inf'))))
            )

        return False

    def save(
        self,
        model: Any,
        step: int,
        epoch: int,
        metric_value: Optional[float] = None,
        metric_name: str = "loss",
        optimizer: Optional[Any] = None,
        scheduler: Optional[Any] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> ModelCheckpoint:
        """
        Save a checkpoint.

        Args:
            model: Model to save
            step: Current training step
            epoch: Current epoch
            metric_value: Current metric value
            metric_name: Name of the metric
            optimizer: Optional optimizer state
            scheduler: Optional scheduler state
            extra_data: Optional extra data to save

        Returns:
            Created checkpoint
        """
        # Generate ID
        ckpt_id = hashlib.md5(
            f"{step}:{epoch}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        # Create checkpoint directory
        ckpt_path = self.checkpoint_dir / f"{self.CHECKPOINT_PREFIX}-{step}"
        ckpt_path.mkdir(parents=True, exist_ok=True)

        # Check if best
        is_best = False
        if metric_value is not None:
            if self._best_checkpoint is None:
                is_best = True
            elif metric_value < (self._best_checkpoint.metric_value or float('inf')):
                is_best = True

        # Create checkpoint object
        checkpoint = ModelCheckpoint(
            id=ckpt_id,
            path=str(ckpt_path),
            step=step,
            epoch=epoch,
            metric_value=metric_value,
            metric_name=metric_name,
            is_best=is_best,
        )

        # Save model
        model_path = ckpt_path / "model.pt"
        self._save_model(model, model_path)
        checkpoint.files.append(str(model_path))

        # Save optimizer
        if optimizer and self.config.save_optimizer_state:
            optimizer_path = ckpt_path / "optimizer.pt"
            self._save_state(optimizer, optimizer_path)
            checkpoint.files.append(str(optimizer_path))

        # Save scheduler
        if scheduler and self.config.save_scheduler_state:
            scheduler_path = ckpt_path / "scheduler.pt"
            self._save_state(scheduler, scheduler_path)
            checkpoint.files.append(str(scheduler_path))

        # Save training state
        training_state = {
            "step": step,
            "epoch": epoch,
            "metric_value": metric_value,
            "metric_name": metric_name,
        }
        if extra_data:
            training_state.update(extra_data)

        state_path = ckpt_path / "training_state.json"
        with open(state_path, 'w') as f:
            json.dump(training_state, f, indent=2)
        checkpoint.files.append(str(state_path))

        # Calculate size
        total_size = sum(
            os.path.getsize(f) for f in checkpoint.files
            if os.path.exists(f)
        )
        checkpoint.model_size_mb = total_size / (1024 * 1024)

        # Add to list
        self._checkpoints.append(checkpoint)
        self._last_checkpoint = checkpoint

        if is_best:
            self._best_checkpoint = checkpoint
            # Create best link
            best_path = self.checkpoint_dir / "best"
            if best_path.exists():
                if best_path.is_symlink():
                    best_path.unlink()
                else:
                    shutil.rmtree(best_path)
            best_path.symlink_to(ckpt_path.name)

        # Prune old checkpoints
        self._prune_checkpoints()

        # Save metadata
        self._save_metadata()

        # Update stats
        self._last_save_time = datetime.now()
        self.stats["checkpoints_saved"] += 1
        self.stats["total_size_mb"] = sum(
            ckpt.model_size_mb for ckpt in self._checkpoints
        )

        logger.info(
            f"Saved checkpoint at step {step} "
            f"(metric={metric_value}, is_best={is_best})"
        )

        return checkpoint

    def _save_model(self, model: Any, path: Path) -> None:
        """Save model weights."""
        # In real implementation:
        # torch.save(model.state_dict(), path)

        # Simulate saving
        path.touch()
        path.write_text(f"# Model weights (simulated)\n# Size: varies")

    def _save_state(self, obj: Any, path: Path) -> None:
        """Save optimizer/scheduler state."""
        # In real implementation:
        # torch.save(obj.state_dict(), path)

        path.touch()

    def load(
        self,
        checkpoint: Optional[ModelCheckpoint] = None,
        checkpoint_path: Optional[str] = None,
        load_best: bool = False,
    ) -> Dict[str, Any]:
        """
        Load a checkpoint.

        Args:
            checkpoint: Checkpoint to load
            checkpoint_path: Or path to checkpoint
            load_best: Load best checkpoint

        Returns:
            Loaded state dictionary
        """
        if load_best:
            checkpoint = self._best_checkpoint

        if checkpoint is None and checkpoint_path:
            # Find checkpoint by path
            for ckpt in self._checkpoints:
                if ckpt.path == checkpoint_path:
                    checkpoint = ckpt
                    break

        if checkpoint is None:
            checkpoint = self._last_checkpoint

        if checkpoint is None:
            raise ValueError("No checkpoint to load")

        ckpt_path = Path(checkpoint.path)

        # Load training state
        state_path = ckpt_path / "training_state.json"
        if state_path.exists():
            with open(state_path, 'r') as f:
                training_state = json.load(f)
        else:
            training_state = {}

        result = {
            "checkpoint": checkpoint,
            "training_state": training_state,
            "model_path": str(ckpt_path / "model.pt"),
            "optimizer_path": str(ckpt_path / "optimizer.pt"),
            "scheduler_path": str(ckpt_path / "scheduler.pt"),
        }

        logger.info(f"Loaded checkpoint from step {checkpoint.step}")

        return result

    def _prune_checkpoints(self) -> None:
        """Prune old checkpoints to meet limit."""
        if len(self._checkpoints) <= self.config.save_total_limit:
            return

        # Sort by step (keep recent)
        sorted_ckpts = sorted(self._checkpoints, key=lambda x: x.step, reverse=True)

        # Determine which to keep
        to_keep = set()

        # Keep best
        if self.config.keep_best and self._best_checkpoint:
            to_keep.add(self._best_checkpoint.id)

        # Keep last
        if self.config.keep_last and self._last_checkpoint:
            to_keep.add(self._last_checkpoint.id)

        # Keep recent up to limit
        for ckpt in sorted_ckpts:
            if len(to_keep) >= self.config.save_total_limit:
                break
            to_keep.add(ckpt.id)

        # Delete others
        for ckpt in list(self._checkpoints):
            if ckpt.id not in to_keep:
                self._delete_checkpoint(ckpt)

    def _delete_checkpoint(self, checkpoint: ModelCheckpoint) -> None:
        """Delete a checkpoint."""
        ckpt_path = Path(checkpoint.path)

        if ckpt_path.exists():
            shutil.rmtree(ckpt_path)

        self._checkpoints.remove(checkpoint)
        self.stats["checkpoints_deleted"] += 1

        logger.info(f"Deleted checkpoint at step {checkpoint.step}")

    def get_latest(self) -> Optional[ModelCheckpoint]:
        """Get latest checkpoint."""
        return self._last_checkpoint

    def get_best(self) -> Optional[ModelCheckpoint]:
        """Get best checkpoint."""
        return self._best_checkpoint

    def list_checkpoints(self) -> List[ModelCheckpoint]:
        """List all checkpoints."""
        return list(self._checkpoints)

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            **self.stats,
            "num_checkpoints": len(self._checkpoints),
            "has_best": self._best_checkpoint is not None,
            "has_latest": self._last_checkpoint is not None,
        }


def demo():
    """Demonstrate checkpoint manager."""
    import tempfile

    print("=" * 60)
    print("BAEL Checkpoint Manager Demo")
    print("=" * 60)

    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        config = CheckpointConfig(
            checkpoint_dir=tmpdir,
            strategy=CheckpointStrategy.STEPS,
            save_steps=100,
            save_total_limit=3,
        )

        manager = CheckpointManager(config)

        print(f"\nConfig:")
        print(f"  Directory: {config.checkpoint_dir}")
        print(f"  Strategy: {config.strategy.value}")
        print(f"  Save steps: {config.save_steps}")
        print(f"  Limit: {config.save_total_limit}")

        # Simulate training
        fake_model = {"weights": "simulated"}

        print("\nSimulating training...")
        for step in range(0, 501, 100):
            # Check if should save
            if manager.should_save(step, step // 100):
                metric = 2.0 - (step / 500)  # Decreasing loss

                ckpt = manager.save(
                    model=fake_model,
                    step=step,
                    epoch=step // 100,
                    metric_value=metric,
                )

                print(f"  Saved step {step}: loss={metric:.4f}, is_best={ckpt.is_best}")

        # List checkpoints
        print("\nCheckpoints:")
        for ckpt in manager.list_checkpoints():
            status = []
            if ckpt.is_best:
                status.append("BEST")
            if ckpt == manager.get_latest():
                status.append("LATEST")
            status_str = f" [{', '.join(status)}]" if status else ""
            print(f"  Step {ckpt.step}: loss={ckpt.metric_value:.4f}{status_str}")

        # Load best
        print("\nLoading best checkpoint...")
        loaded = manager.load(load_best=True)
        print(f"  Step: {loaded['checkpoint'].step}")
        print(f"  Metric: {loaded['checkpoint'].metric_value}")

        print(f"\nStats: {manager.get_stats()}")


if __name__ == "__main__":
    demo()
