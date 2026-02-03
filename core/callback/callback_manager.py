#!/usr/bin/env python3
"""
BAEL - Callback Manager
Comprehensive training callbacks for AI pipelines.

Features:
- Epoch/step callbacks
- Learning rate scheduling callbacks
- Early stopping callback
- Model checkpoint callback
- Logging callbacks
- Custom callback support
"""

import asyncio
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class CallbackEvent(Enum):
    """Callback event types."""
    TRAIN_BEGIN = "train_begin"
    TRAIN_END = "train_end"
    EPOCH_BEGIN = "epoch_begin"
    EPOCH_END = "epoch_end"
    BATCH_BEGIN = "batch_begin"
    BATCH_END = "batch_end"
    VALIDATION_BEGIN = "validation_begin"
    VALIDATION_END = "validation_end"
    PREDICT_BEGIN = "predict_begin"
    PREDICT_END = "predict_end"


class CallbackPriority(Enum):
    """Callback priority levels."""
    HIGHEST = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    LOWEST = 4


class CallbackAction(Enum):
    """Actions a callback can request."""
    CONTINUE = "continue"
    STOP_TRAINING = "stop_training"
    STOP_BATCH = "stop_batch"
    SKIP = "skip"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class TrainingState:
    """Current training state passed to callbacks."""
    epoch: int = 0
    total_epochs: int = 0
    batch: int = 0
    total_batches: int = 0
    global_step: int = 0
    metrics: Dict[str, float] = field(default_factory=dict)
    loss: float = 0.0
    learning_rate: float = 0.001
    is_training: bool = True
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CallbackResult:
    """Result from callback execution."""
    callback_id: str = ""
    action: CallbackAction = CallbackAction.CONTINUE
    message: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class CallbackStats:
    """Statistics for callback execution."""
    total_calls: int = 0
    by_event: Dict[str, int] = field(default_factory=dict)
    total_time_ms: float = 0.0
    errors: int = 0


# =============================================================================
# CALLBACK BASE
# =============================================================================

class Callback(ABC):
    """Abstract base callback."""

    def __init__(
        self,
        priority: CallbackPriority = CallbackPriority.NORMAL
    ):
        self.callback_id = str(uuid.uuid4())
        self.priority = priority
        self.enabled = True

    def on_train_begin(self, state: TrainingState) -> CallbackResult:
        """Called at training start."""
        return CallbackResult(callback_id=self.callback_id)

    def on_train_end(self, state: TrainingState) -> CallbackResult:
        """Called at training end."""
        return CallbackResult(callback_id=self.callback_id)

    def on_epoch_begin(self, state: TrainingState) -> CallbackResult:
        """Called at epoch start."""
        return CallbackResult(callback_id=self.callback_id)

    def on_epoch_end(self, state: TrainingState) -> CallbackResult:
        """Called at epoch end."""
        return CallbackResult(callback_id=self.callback_id)

    def on_batch_begin(self, state: TrainingState) -> CallbackResult:
        """Called at batch start."""
        return CallbackResult(callback_id=self.callback_id)

    def on_batch_end(self, state: TrainingState) -> CallbackResult:
        """Called at batch end."""
        return CallbackResult(callback_id=self.callback_id)

    def on_validation_begin(self, state: TrainingState) -> CallbackResult:
        """Called at validation start."""
        return CallbackResult(callback_id=self.callback_id)

    def on_validation_end(self, state: TrainingState) -> CallbackResult:
        """Called at validation end."""
        return CallbackResult(callback_id=self.callback_id)


# =============================================================================
# BUILT-IN CALLBACKS
# =============================================================================

class EarlyStoppingCallback(Callback):
    """Early stopping callback."""

    def __init__(
        self,
        monitor: str = "val_loss",
        patience: int = 10,
        min_delta: float = 0.0,
        mode: str = "min",
        restore_best: bool = True
    ):
        super().__init__(CallbackPriority.HIGH)
        self._monitor = monitor
        self._patience = patience
        self._min_delta = min_delta
        self._mode = mode
        self._restore_best = restore_best
        self._counter = 0
        self._best_value: Optional[float] = None
        self._best_epoch = 0
        self._stopped_epoch = 0

    def on_epoch_end(self, state: TrainingState) -> CallbackResult:
        """Check for early stopping."""
        current = state.metrics.get(self._monitor)

        if current is None:
            return CallbackResult(
                callback_id=self.callback_id,
                message=f"Metric {self._monitor} not found"
            )

        if self._best_value is None:
            self._best_value = current
            self._best_epoch = state.epoch
            return CallbackResult(callback_id=self.callback_id)

        if self._mode == "min":
            improved = current < self._best_value - self._min_delta
        else:
            improved = current > self._best_value + self._min_delta

        if improved:
            self._best_value = current
            self._best_epoch = state.epoch
            self._counter = 0
        else:
            self._counter += 1

        if self._counter >= self._patience:
            self._stopped_epoch = state.epoch
            return CallbackResult(
                callback_id=self.callback_id,
                action=CallbackAction.STOP_TRAINING,
                message=f"Early stopping at epoch {state.epoch}"
            )

        return CallbackResult(callback_id=self.callback_id)

    @property
    def best_epoch(self) -> int:
        return self._best_epoch

    @property
    def stopped_epoch(self) -> int:
        return self._stopped_epoch


class LearningRateSchedulerCallback(Callback):
    """Learning rate scheduler callback."""

    def __init__(
        self,
        schedule_fn: Optional[Callable[[int, float], float]] = None,
        step_on: str = "epoch",
        verbose: bool = False
    ):
        super().__init__(CallbackPriority.HIGH)
        self._schedule_fn = schedule_fn or self._default_schedule
        self._step_on = step_on
        self._verbose = verbose
        self._lr_history: List[float] = []

    def _default_schedule(self, step: int, lr: float) -> float:
        """Default exponential decay."""
        return lr * 0.95

    def on_epoch_end(self, state: TrainingState) -> CallbackResult:
        """Update learning rate at epoch end."""
        if self._step_on != "epoch":
            return CallbackResult(callback_id=self.callback_id)

        old_lr = state.learning_rate
        new_lr = self._schedule_fn(state.epoch, old_lr)
        self._lr_history.append(new_lr)

        return CallbackResult(
            callback_id=self.callback_id,
            metrics={"learning_rate": new_lr},
            message=f"LR: {old_lr:.6f} -> {new_lr:.6f}" if self._verbose else None
        )

    def on_batch_end(self, state: TrainingState) -> CallbackResult:
        """Update learning rate at batch end."""
        if self._step_on != "batch":
            return CallbackResult(callback_id=self.callback_id)

        old_lr = state.learning_rate
        new_lr = self._schedule_fn(state.global_step, old_lr)
        self._lr_history.append(new_lr)

        return CallbackResult(
            callback_id=self.callback_id,
            metrics={"learning_rate": new_lr}
        )

    @property
    def lr_history(self) -> List[float]:
        return self._lr_history.copy()


class ModelCheckpointCallback(Callback):
    """Model checkpoint callback."""

    def __init__(
        self,
        filepath: str = "model_{epoch}",
        monitor: str = "val_loss",
        save_best_only: bool = True,
        mode: str = "min",
        save_frequency: int = 1,
        verbose: bool = False
    ):
        super().__init__(CallbackPriority.NORMAL)
        self._filepath = filepath
        self._monitor = monitor
        self._save_best_only = save_best_only
        self._mode = mode
        self._save_frequency = save_frequency
        self._verbose = verbose
        self._best_value: Optional[float] = None
        self._saved_paths: List[str] = []

    def _should_save(self, current: float) -> bool:
        """Determine if should save."""
        if not self._save_best_only:
            return True

        if self._best_value is None:
            self._best_value = current
            return True

        if self._mode == "min":
            is_better = current < self._best_value
        else:
            is_better = current > self._best_value

        if is_better:
            self._best_value = current
            return True

        return False

    def on_epoch_end(self, state: TrainingState) -> CallbackResult:
        """Check for checkpoint save."""
        if state.epoch % self._save_frequency != 0:
            return CallbackResult(callback_id=self.callback_id)

        current = state.metrics.get(self._monitor, state.loss)

        if self._should_save(current):
            path = self._filepath.format(epoch=state.epoch)
            self._saved_paths.append(path)

            return CallbackResult(
                callback_id=self.callback_id,
                message=f"Saved checkpoint: {path}" if self._verbose else None,
                metrics={"checkpoint_saved": 1.0}
            )

        return CallbackResult(callback_id=self.callback_id)

    @property
    def saved_paths(self) -> List[str]:
        return self._saved_paths.copy()


class ProgressCallback(Callback):
    """Progress tracking callback."""

    def __init__(self, verbose: int = 1):
        super().__init__(CallbackPriority.LOW)
        self._verbose = verbose
        self._epoch_logs: List[Dict[str, Any]] = []

    def on_epoch_begin(self, state: TrainingState) -> CallbackResult:
        """Log epoch start."""
        if self._verbose >= 1:
            return CallbackResult(
                callback_id=self.callback_id,
                message=f"Epoch {state.epoch + 1}/{state.total_epochs}"
            )
        return CallbackResult(callback_id=self.callback_id)

    def on_epoch_end(self, state: TrainingState) -> CallbackResult:
        """Log epoch end."""
        log = {
            "epoch": state.epoch,
            "loss": state.loss,
            **state.metrics
        }
        self._epoch_logs.append(log)

        if self._verbose >= 1:
            metrics_str = ", ".join(
                f"{k}: {v:.4f}" for k, v in state.metrics.items()
            )
            return CallbackResult(
                callback_id=self.callback_id,
                message=f"loss: {state.loss:.4f} - {metrics_str}"
            )

        return CallbackResult(callback_id=self.callback_id)

    @property
    def epoch_logs(self) -> List[Dict[str, Any]]:
        return self._epoch_logs.copy()


class TerminateOnNaNCallback(Callback):
    """Terminate training on NaN loss."""

    def __init__(self):
        super().__init__(CallbackPriority.HIGHEST)

    def on_batch_end(self, state: TrainingState) -> CallbackResult:
        """Check for NaN loss."""
        if math.isnan(state.loss) or math.isinf(state.loss):
            return CallbackResult(
                callback_id=self.callback_id,
                action=CallbackAction.STOP_TRAINING,
                message=f"NaN/Inf loss detected: {state.loss}"
            )
        return CallbackResult(callback_id=self.callback_id)


class MetricHistoryCallback(Callback):
    """Track metric history."""

    def __init__(self, metrics: Optional[List[str]] = None):
        super().__init__(CallbackPriority.LOW)
        self._tracked = metrics
        self._history: Dict[str, List[float]] = defaultdict(list)

    def on_epoch_end(self, state: TrainingState) -> CallbackResult:
        """Record metrics."""
        self._history["loss"].append(state.loss)

        for name, value in state.metrics.items():
            if self._tracked is None or name in self._tracked:
                self._history[name].append(value)

        return CallbackResult(callback_id=self.callback_id)

    def get_history(self, metric: str) -> List[float]:
        """Get history for metric."""
        return self._history.get(metric, []).copy()

    @property
    def history(self) -> Dict[str, List[float]]:
        return dict(self._history)


class LambdaCallback(Callback):
    """Custom callback with lambda functions."""

    def __init__(
        self,
        on_train_begin: Optional[Callable] = None,
        on_train_end: Optional[Callable] = None,
        on_epoch_begin: Optional[Callable] = None,
        on_epoch_end: Optional[Callable] = None,
        on_batch_begin: Optional[Callable] = None,
        on_batch_end: Optional[Callable] = None
    ):
        super().__init__()
        self._on_train_begin = on_train_begin
        self._on_train_end = on_train_end
        self._on_epoch_begin = on_epoch_begin
        self._on_epoch_end = on_epoch_end
        self._on_batch_begin = on_batch_begin
        self._on_batch_end = on_batch_end

    def on_train_begin(self, state: TrainingState) -> CallbackResult:
        if self._on_train_begin:
            self._on_train_begin(state)
        return CallbackResult(callback_id=self.callback_id)

    def on_train_end(self, state: TrainingState) -> CallbackResult:
        if self._on_train_end:
            self._on_train_end(state)
        return CallbackResult(callback_id=self.callback_id)

    def on_epoch_begin(self, state: TrainingState) -> CallbackResult:
        if self._on_epoch_begin:
            self._on_epoch_begin(state)
        return CallbackResult(callback_id=self.callback_id)

    def on_epoch_end(self, state: TrainingState) -> CallbackResult:
        if self._on_epoch_end:
            self._on_epoch_end(state)
        return CallbackResult(callback_id=self.callback_id)

    def on_batch_begin(self, state: TrainingState) -> CallbackResult:
        if self._on_batch_begin:
            self._on_batch_begin(state)
        return CallbackResult(callback_id=self.callback_id)

    def on_batch_end(self, state: TrainingState) -> CallbackResult:
        if self._on_batch_end:
            self._on_batch_end(state)
        return CallbackResult(callback_id=self.callback_id)


# =============================================================================
# CALLBACK MANAGER
# =============================================================================

class CallbackManager:
    """
    Callback Manager for BAEL.

    Comprehensive training callbacks for AI pipelines.
    """

    def __init__(self):
        self._callbacks: List[Callback] = []
        self._stats = CallbackStats()
        self._logs: List[str] = []

    def add(self, callback: Callback) -> None:
        """Add callback."""
        self._callbacks.append(callback)
        self._sort_callbacks()

    def remove(self, callback_id: str) -> bool:
        """Remove callback by ID."""
        for i, cb in enumerate(self._callbacks):
            if cb.callback_id == callback_id:
                self._callbacks.pop(i)
                return True
        return False

    def _sort_callbacks(self) -> None:
        """Sort callbacks by priority."""
        self._callbacks.sort(key=lambda c: c.priority.value)

    def _run_event(
        self,
        event: CallbackEvent,
        state: TrainingState
    ) -> CallbackAction:
        """Run all callbacks for event."""
        action = CallbackAction.CONTINUE

        for callback in self._callbacks:
            if not callback.enabled:
                continue

            try:
                handler = getattr(callback, f"on_{event.value}", None)
                if handler:
                    result = handler(state)

                    self._stats.total_calls += 1
                    self._stats.by_event[event.value] = \
                        self._stats.by_event.get(event.value, 0) + 1

                    if result.message:
                        self._logs.append(result.message)

                    if result.action != CallbackAction.CONTINUE:
                        action = result.action

                        if action == CallbackAction.STOP_TRAINING:
                            break

            except Exception as e:
                self._stats.errors += 1
                self._logs.append(f"Callback error: {e}")

        return action

    def on_train_begin(self, state: TrainingState) -> CallbackAction:
        """Trigger train begin callbacks."""
        return self._run_event(CallbackEvent.TRAIN_BEGIN, state)

    def on_train_end(self, state: TrainingState) -> CallbackAction:
        """Trigger train end callbacks."""
        return self._run_event(CallbackEvent.TRAIN_END, state)

    def on_epoch_begin(self, state: TrainingState) -> CallbackAction:
        """Trigger epoch begin callbacks."""
        return self._run_event(CallbackEvent.EPOCH_BEGIN, state)

    def on_epoch_end(self, state: TrainingState) -> CallbackAction:
        """Trigger epoch end callbacks."""
        return self._run_event(CallbackEvent.EPOCH_END, state)

    def on_batch_begin(self, state: TrainingState) -> CallbackAction:
        """Trigger batch begin callbacks."""
        return self._run_event(CallbackEvent.BATCH_BEGIN, state)

    def on_batch_end(self, state: TrainingState) -> CallbackAction:
        """Trigger batch end callbacks."""
        return self._run_event(CallbackEvent.BATCH_END, state)

    def on_validation_begin(self, state: TrainingState) -> CallbackAction:
        """Trigger validation begin callbacks."""
        return self._run_event(CallbackEvent.VALIDATION_BEGIN, state)

    def on_validation_end(self, state: TrainingState) -> CallbackAction:
        """Trigger validation end callbacks."""
        return self._run_event(CallbackEvent.VALIDATION_END, state)

    def get_callback(self, callback_type: Type[Callback]) -> Optional[Callback]:
        """Get callback by type."""
        for cb in self._callbacks:
            if isinstance(cb, callback_type):
                return cb
        return None

    def get_stats(self) -> CallbackStats:
        """Get callback statistics."""
        return self._stats

    def get_logs(self) -> List[str]:
        """Get callback logs."""
        return self._logs.copy()

    def clear_logs(self) -> None:
        """Clear logs."""
        self._logs.clear()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Callback Manager."""
    print("=" * 70)
    print("BAEL - CALLBACK MANAGER DEMO")
    print("Comprehensive Training Callbacks for AI Pipelines")
    print("=" * 70)
    print()

    manager = CallbackManager()

    # 1. Add Callbacks
    print("1. ADDING CALLBACKS:")
    print("-" * 40)

    early_stop = EarlyStoppingCallback(
        monitor="val_loss",
        patience=3,
        min_delta=0.01
    )
    manager.add(early_stop)
    print("   Added: EarlyStopping (patience=3)")

    lr_scheduler = LearningRateSchedulerCallback(
        schedule_fn=lambda step, lr: lr * 0.9,
        verbose=True
    )
    manager.add(lr_scheduler)
    print("   Added: LearningRateScheduler")

    checkpoint = ModelCheckpointCallback(
        filepath="model_{epoch}",
        save_best_only=True,
        verbose=True
    )
    manager.add(checkpoint)
    print("   Added: ModelCheckpoint")

    progress = ProgressCallback(verbose=1)
    manager.add(progress)
    print("   Added: Progress")

    history = MetricHistoryCallback()
    manager.add(history)
    print("   Added: MetricHistory")

    nan_check = TerminateOnNaNCallback()
    manager.add(nan_check)
    print("   Added: TerminateOnNaN")
    print()

    # 2. Simulate Training
    print("2. SIMULATING TRAINING:")
    print("-" * 40)

    state = TrainingState(
        total_epochs=10,
        total_batches=100,
        learning_rate=0.01
    )

    manager.on_train_begin(state)
    print("   Training started...")

    losses = [1.0, 0.8, 0.6, 0.55, 0.54, 0.53, 0.52, 0.51]

    for epoch in range(8):
        state.epoch = epoch

        manager.on_epoch_begin(state)

        for batch in range(10):
            state.batch = batch
            state.global_step = epoch * 10 + batch
            state.loss = losses[epoch] + random.uniform(-0.02, 0.02)

            action = manager.on_batch_end(state)
            if action == CallbackAction.STOP_TRAINING:
                print(f"   Stopped at batch {batch}")
                break

        state.metrics = {
            "val_loss": losses[epoch],
            "val_accuracy": 0.5 + epoch * 0.05
        }

        action = manager.on_epoch_end(state)

        print(f"   Epoch {epoch + 1}: loss={state.loss:.4f}, val_loss={losses[epoch]:.4f}")

        if action == CallbackAction.STOP_TRAINING:
            print("   Early stopping triggered!")
            break

    manager.on_train_end(state)
    print()

    # 3. Early Stopping Status
    print("3. EARLY STOPPING STATUS:")
    print("-" * 40)

    es = manager.get_callback(EarlyStoppingCallback)
    if es:
        print(f"   Best epoch: {es.best_epoch}")
        print(f"   Stopped epoch: {es.stopped_epoch}")
    print()

    # 4. Checkpoint Status
    print("4. CHECKPOINT STATUS:")
    print("-" * 40)

    cp = manager.get_callback(ModelCheckpointCallback)
    if cp:
        print(f"   Saved checkpoints: {len(cp.saved_paths)}")
        for path in cp.saved_paths:
            print(f"      - {path}")
    print()

    # 5. Learning Rate History
    print("5. LEARNING RATE HISTORY:")
    print("-" * 40)

    lr = manager.get_callback(LearningRateSchedulerCallback)
    if lr and lr.lr_history:
        print(f"   LR values: {[f'{v:.6f}' for v in lr.lr_history[:5]]}...")
    print()

    # 6. Metric History
    print("6. METRIC HISTORY:")
    print("-" * 40)

    hist = manager.get_callback(MetricHistoryCallback)
    if hist:
        loss_hist = hist.get_history("loss")
        print(f"   Loss history: {[f'{l:.4f}' for l in loss_hist[:5]]}...")
        val_acc_hist = hist.get_history("val_accuracy")
        print(f"   Val acc history: {[f'{a:.4f}' for a in val_acc_hist[:5]]}...")
    print()

    # 7. Lambda Callback
    print("7. LAMBDA CALLBACK:")
    print("-" * 40)

    custom_data = {"epochs_seen": 0}

    lambda_cb = LambdaCallback(
        on_epoch_end=lambda s: custom_data.update({"epochs_seen": s.epoch + 1})
    )
    manager.add(lambda_cb)

    for epoch in range(3):
        state.epoch = epoch
        manager.on_epoch_end(state)

    print(f"   Epochs tracked by lambda: {custom_data['epochs_seen']}")
    print()

    # 8. Callback Stats
    print("8. CALLBACK STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()
    print(f"   Total calls: {stats.total_calls}")
    print(f"   By event: {dict(stats.by_event)}")
    print(f"   Errors: {stats.errors}")
    print()

    # 9. Callback Logs
    print("9. CALLBACK LOGS (last 5):")
    print("-" * 40)

    logs = manager.get_logs()
    for log in logs[-5:]:
        print(f"   {log}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Callback Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
