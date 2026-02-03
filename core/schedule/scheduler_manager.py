#!/usr/bin/env python3
"""
BAEL - Scheduler Manager
Comprehensive learning rate and training scheduling.

Features:
- Step decay scheduling
- Exponential decay scheduling
- Cosine annealing
- Warmup scheduling
- Cyclic learning rates
- One-cycle policy
"""

import asyncio
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, List, Optional, Sequence, Tuple, Type,
                    TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class SchedulerType(Enum):
    """Scheduler types."""
    CONSTANT = "constant"
    STEP = "step"
    MULTISTEP = "multistep"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    POLYNOMIAL = "polynomial"
    COSINE = "cosine"
    COSINE_RESTART = "cosine_restart"
    CYCLIC = "cyclic"
    ONECYCLE = "onecycle"
    WARMUP = "warmup"
    REDUCE_ON_PLATEAU = "reduce_on_plateau"
    CUSTOM = "custom"


class CyclicMode(Enum):
    """Cyclic learning rate modes."""
    TRIANGULAR = "triangular"
    TRIANGULAR2 = "triangular2"
    EXPONENTIAL_RANGE = "exponential_range"


class WarmupType(Enum):
    """Warmup types."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    COSINE = "cosine"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class SchedulerState:
    """Scheduler state."""
    step: int = 0
    epoch: int = 0
    current_lr: float = 0.0
    base_lr: float = 0.0
    best_metric: Optional[float] = None
    bad_epochs: int = 0
    last_update: Optional[datetime] = None


@dataclass
class SchedulerConfig:
    """Scheduler configuration."""
    base_lr: float = 0.01
    min_lr: float = 1e-7
    max_lr: float = 0.1
    warmup_epochs: int = 0
    warmup_type: WarmupType = WarmupType.LINEAR
    total_epochs: int = 100
    last_epoch: int = -1


@dataclass
class LRStep:
    """Learning rate step record."""
    epoch: int
    step: int
    lr: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ScheduleHistory:
    """Schedule history."""
    steps: List[LRStep] = field(default_factory=list)
    min_lr: float = float('inf')
    max_lr: float = float('-inf')
    total_steps: int = 0


# =============================================================================
# BASE SCHEDULER
# =============================================================================

class BaseScheduler(ABC):
    """Abstract base scheduler."""

    def __init__(
        self,
        config: Optional[SchedulerConfig] = None,
        name: Optional[str] = None
    ):
        self.config = config or SchedulerConfig()
        self.name = name or self.__class__.__name__
        self.state = SchedulerState(
            current_lr=self.config.base_lr,
            base_lr=self.config.base_lr
        )
        self.history = ScheduleHistory()

    @abstractmethod
    def _compute_lr(self, epoch: int, step: int) -> float:
        """Compute learning rate for epoch/step."""
        pass

    def step(self, epoch: Optional[int] = None) -> float:
        """Advance scheduler and get new LR."""
        if epoch is not None:
            self.state.epoch = epoch
        else:
            self.state.epoch += 1

        self.state.step += 1

        warmup_lr = self._apply_warmup()
        if warmup_lr is not None:
            self.state.current_lr = warmup_lr
        else:
            self.state.current_lr = self._compute_lr(
                self.state.epoch,
                self.state.step
            )

        self.state.current_lr = max(self.config.min_lr, self.state.current_lr)
        self.state.last_update = datetime.now()

        lr_step = LRStep(
            epoch=self.state.epoch,
            step=self.state.step,
            lr=self.state.current_lr
        )
        self.history.steps.append(lr_step)
        self.history.min_lr = min(self.history.min_lr, self.state.current_lr)
        self.history.max_lr = max(self.history.max_lr, self.state.current_lr)
        self.history.total_steps += 1

        return self.state.current_lr

    def _apply_warmup(self) -> Optional[float]:
        """Apply warmup if applicable."""
        if self.state.epoch >= self.config.warmup_epochs:
            return None

        warmup_factor = (self.state.epoch + 1) / self.config.warmup_epochs

        if self.config.warmup_type == WarmupType.LINEAR:
            factor = warmup_factor
        elif self.config.warmup_type == WarmupType.EXPONENTIAL:
            factor = math.exp((warmup_factor - 1) * 3)
        elif self.config.warmup_type == WarmupType.COSINE:
            factor = 0.5 * (1 - math.cos(math.pi * warmup_factor))
        else:
            factor = warmup_factor

        return self.config.base_lr * factor

    def get_lr(self) -> float:
        """Get current learning rate."""
        return self.state.current_lr

    def reset(self) -> None:
        """Reset scheduler state."""
        self.state = SchedulerState(
            current_lr=self.config.base_lr,
            base_lr=self.config.base_lr
        )
        self.history = ScheduleHistory()


# =============================================================================
# SCHEDULER IMPLEMENTATIONS
# =============================================================================

class ConstantScheduler(BaseScheduler):
    """Constant learning rate scheduler."""

    def __init__(self, config: Optional[SchedulerConfig] = None):
        super().__init__(config, "ConstantScheduler")

    def _compute_lr(self, epoch: int, step: int) -> float:
        """Return constant LR."""
        return self.config.base_lr


class StepScheduler(BaseScheduler):
    """Step decay scheduler."""

    def __init__(
        self,
        step_size: int = 10,
        gamma: float = 0.1,
        config: Optional[SchedulerConfig] = None
    ):
        super().__init__(config, "StepScheduler")
        self._step_size = step_size
        self._gamma = gamma

    def _compute_lr(self, epoch: int, step: int) -> float:
        """Compute step decay LR."""
        return self.config.base_lr * (self._gamma ** (epoch // self._step_size))


class MultiStepScheduler(BaseScheduler):
    """Multi-step decay scheduler."""

    def __init__(
        self,
        milestones: List[int] = None,
        gamma: float = 0.1,
        config: Optional[SchedulerConfig] = None
    ):
        super().__init__(config, "MultiStepScheduler")
        self._milestones = sorted(milestones or [30, 60, 90])
        self._gamma = gamma

    def _compute_lr(self, epoch: int, step: int) -> float:
        """Compute multi-step decay LR."""
        num_decays = sum(1 for m in self._milestones if epoch >= m)
        return self.config.base_lr * (self._gamma ** num_decays)


class ExponentialScheduler(BaseScheduler):
    """Exponential decay scheduler."""

    def __init__(
        self,
        gamma: float = 0.95,
        config: Optional[SchedulerConfig] = None
    ):
        super().__init__(config, "ExponentialScheduler")
        self._gamma = gamma

    def _compute_lr(self, epoch: int, step: int) -> float:
        """Compute exponential decay LR."""
        return self.config.base_lr * (self._gamma ** epoch)


class LinearScheduler(BaseScheduler):
    """Linear decay scheduler."""

    def __init__(self, config: Optional[SchedulerConfig] = None):
        super().__init__(config, "LinearScheduler")

    def _compute_lr(self, epoch: int, step: int) -> float:
        """Compute linear decay LR."""
        if epoch >= self.config.total_epochs:
            return self.config.min_lr

        factor = 1.0 - (epoch / self.config.total_epochs)
        return self.config.base_lr * factor


class PolynomialScheduler(BaseScheduler):
    """Polynomial decay scheduler."""

    def __init__(
        self,
        power: float = 1.0,
        config: Optional[SchedulerConfig] = None
    ):
        super().__init__(config, "PolynomialScheduler")
        self._power = power

    def _compute_lr(self, epoch: int, step: int) -> float:
        """Compute polynomial decay LR."""
        if epoch >= self.config.total_epochs:
            return self.config.min_lr

        factor = (1.0 - epoch / self.config.total_epochs) ** self._power
        return self.config.base_lr * factor


class CosineScheduler(BaseScheduler):
    """Cosine annealing scheduler."""

    def __init__(self, config: Optional[SchedulerConfig] = None):
        super().__init__(config, "CosineScheduler")

    def _compute_lr(self, epoch: int, step: int) -> float:
        """Compute cosine annealing LR."""
        if epoch >= self.config.total_epochs:
            return self.config.min_lr

        cos_factor = math.cos(math.pi * epoch / self.config.total_epochs)
        return self.config.min_lr + (self.config.base_lr - self.config.min_lr) * 0.5 * (1 + cos_factor)


class CosineRestartScheduler(BaseScheduler):
    """Cosine annealing with warm restarts."""

    def __init__(
        self,
        t_0: int = 10,
        t_mult: int = 2,
        config: Optional[SchedulerConfig] = None
    ):
        super().__init__(config, "CosineRestartScheduler")
        self._t_0 = t_0
        self._t_mult = t_mult

    def _compute_lr(self, epoch: int, step: int) -> float:
        """Compute cosine annealing with restarts LR."""
        t_i = self._t_0
        t_cur = epoch

        while t_cur >= t_i:
            t_cur -= t_i
            t_i = int(t_i * self._t_mult)

        cos_factor = math.cos(math.pi * t_cur / t_i)
        return self.config.min_lr + (self.config.base_lr - self.config.min_lr) * 0.5 * (1 + cos_factor)


class CyclicScheduler(BaseScheduler):
    """Cyclic learning rate scheduler."""

    def __init__(
        self,
        step_size_up: int = 10,
        step_size_down: Optional[int] = None,
        mode: CyclicMode = CyclicMode.TRIANGULAR,
        gamma: float = 0.99,
        config: Optional[SchedulerConfig] = None
    ):
        super().__init__(config, "CyclicScheduler")
        self._step_size_up = step_size_up
        self._step_size_down = step_size_down or step_size_up
        self._mode = mode
        self._gamma = gamma

    def _compute_lr(self, epoch: int, step: int) -> float:
        """Compute cyclic LR."""
        cycle_size = self._step_size_up + self._step_size_down
        cycle = epoch // cycle_size
        position = epoch % cycle_size

        if position <= self._step_size_up:
            factor = position / self._step_size_up
        else:
            factor = 1 - (position - self._step_size_up) / self._step_size_down

        if self._mode == CyclicMode.TRIANGULAR:
            amplitude = 1.0
        elif self._mode == CyclicMode.TRIANGULAR2:
            amplitude = 1.0 / (2 ** cycle)
        elif self._mode == CyclicMode.EXPONENTIAL_RANGE:
            amplitude = self._gamma ** epoch
        else:
            amplitude = 1.0

        lr_range = (self.config.max_lr - self.config.base_lr) * amplitude
        return self.config.base_lr + lr_range * factor


class OneCycleScheduler(BaseScheduler):
    """One-cycle learning rate scheduler."""

    def __init__(
        self,
        pct_start: float = 0.3,
        div_factor: float = 25.0,
        final_div_factor: float = 1e4,
        config: Optional[SchedulerConfig] = None
    ):
        super().__init__(config, "OneCycleScheduler")
        self._pct_start = pct_start
        self._div_factor = div_factor
        self._final_div_factor = final_div_factor

    def _compute_lr(self, epoch: int, step: int) -> float:
        """Compute one-cycle LR."""
        total = self.config.total_epochs
        pct = epoch / total

        initial_lr = self.config.max_lr / self._div_factor
        final_lr = self.config.max_lr / self._final_div_factor

        if pct < self._pct_start:
            factor = pct / self._pct_start
            return initial_lr + (self.config.max_lr - initial_lr) * factor
        else:
            factor = (pct - self._pct_start) / (1 - self._pct_start)
            cos_factor = (1 + math.cos(math.pi * factor)) / 2
            return final_lr + (self.config.max_lr - final_lr) * cos_factor


class ReduceOnPlateauScheduler(BaseScheduler):
    """Reduce on plateau scheduler."""

    def __init__(
        self,
        factor: float = 0.1,
        patience: int = 10,
        threshold: float = 1e-4,
        mode: str = "min",
        config: Optional[SchedulerConfig] = None
    ):
        super().__init__(config, "ReduceOnPlateauScheduler")
        self._factor = factor
        self._patience = patience
        self._threshold = threshold
        self._mode = mode
        self._current_lr = config.base_lr if config else 0.01

    def _compute_lr(self, epoch: int, step: int) -> float:
        """Return current LR (modified by step_with_metric)."""
        return self._current_lr

    def step_with_metric(self, metric: float, epoch: Optional[int] = None) -> float:
        """Step with metric value."""
        if epoch is not None:
            self.state.epoch = epoch

        improved = False

        if self.state.best_metric is None:
            improved = True
        elif self._mode == "min":
            improved = metric < (self.state.best_metric - self._threshold)
        else:
            improved = metric > (self.state.best_metric + self._threshold)

        if improved:
            self.state.best_metric = metric
            self.state.bad_epochs = 0
        else:
            self.state.bad_epochs += 1

            if self.state.bad_epochs >= self._patience:
                self._current_lr *= self._factor
                self._current_lr = max(self.config.min_lr, self._current_lr)
                self.state.bad_epochs = 0

        self.state.current_lr = self._current_lr
        return self._current_lr


# =============================================================================
# SCHEDULER MANAGER
# =============================================================================

class SchedulerManager:
    """
    Scheduler Manager for BAEL.

    Comprehensive learning rate and training scheduling.
    """

    def __init__(self):
        self._schedulers: Dict[str, BaseScheduler] = {}
        self._active: Optional[str] = None

    def create_scheduler(
        self,
        name: str,
        scheduler_type: SchedulerType,
        config: Optional[SchedulerConfig] = None,
        **kwargs
    ) -> BaseScheduler:
        """Create and register scheduler."""
        if scheduler_type == SchedulerType.CONSTANT:
            scheduler = ConstantScheduler(config)
        elif scheduler_type == SchedulerType.STEP:
            scheduler = StepScheduler(config=config, **kwargs)
        elif scheduler_type == SchedulerType.MULTISTEP:
            scheduler = MultiStepScheduler(config=config, **kwargs)
        elif scheduler_type == SchedulerType.EXPONENTIAL:
            scheduler = ExponentialScheduler(config=config, **kwargs)
        elif scheduler_type == SchedulerType.LINEAR:
            scheduler = LinearScheduler(config)
        elif scheduler_type == SchedulerType.POLYNOMIAL:
            scheduler = PolynomialScheduler(config=config, **kwargs)
        elif scheduler_type == SchedulerType.COSINE:
            scheduler = CosineScheduler(config)
        elif scheduler_type == SchedulerType.COSINE_RESTART:
            scheduler = CosineRestartScheduler(config=config, **kwargs)
        elif scheduler_type == SchedulerType.CYCLIC:
            scheduler = CyclicScheduler(config=config, **kwargs)
        elif scheduler_type == SchedulerType.ONECYCLE:
            scheduler = OneCycleScheduler(config=config, **kwargs)
        elif scheduler_type == SchedulerType.REDUCE_ON_PLATEAU:
            scheduler = ReduceOnPlateauScheduler(config=config, **kwargs)
        else:
            scheduler = ConstantScheduler(config)

        self._schedulers[name] = scheduler

        if self._active is None:
            self._active = name

        return scheduler

    def get_scheduler(self, name: str) -> Optional[BaseScheduler]:
        """Get scheduler by name."""
        return self._schedulers.get(name)

    def set_active(self, name: str) -> bool:
        """Set active scheduler."""
        if name in self._schedulers:
            self._active = name
            return True
        return False

    def step(self, name: Optional[str] = None, epoch: Optional[int] = None) -> float:
        """Step scheduler."""
        scheduler_name = name or self._active
        if not scheduler_name or scheduler_name not in self._schedulers:
            return 0.0
        return self._schedulers[scheduler_name].step(epoch)

    def get_lr(self, name: Optional[str] = None) -> float:
        """Get current learning rate."""
        scheduler_name = name or self._active
        if not scheduler_name or scheduler_name not in self._schedulers:
            return 0.0
        return self._schedulers[scheduler_name].get_lr()

    def get_history(self, name: Optional[str] = None) -> Optional[ScheduleHistory]:
        """Get scheduler history."""
        scheduler_name = name or self._active
        if not scheduler_name or scheduler_name not in self._schedulers:
            return None
        return self._schedulers[scheduler_name].history

    def reset(self, name: Optional[str] = None) -> None:
        """Reset scheduler."""
        scheduler_name = name or self._active
        if scheduler_name and scheduler_name in self._schedulers:
            self._schedulers[scheduler_name].reset()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Scheduler Manager."""
    print("=" * 70)
    print("BAEL - SCHEDULER MANAGER DEMO")
    print("Comprehensive Learning Rate and Training Scheduling")
    print("=" * 70)
    print()

    manager = SchedulerManager()

    config = SchedulerConfig(
        base_lr=0.1,
        min_lr=1e-6,
        max_lr=0.1,
        total_epochs=50
    )

    # 1. Step Decay
    print("1. STEP DECAY SCHEDULER:")
    print("-" * 40)

    step_scheduler = manager.create_scheduler(
        "step",
        SchedulerType.STEP,
        config=config,
        step_size=10,
        gamma=0.5
    )

    lrs = []
    for epoch in range(30):
        lr = manager.step("step")
        lrs.append(lr)

    print(f"   Epochs 0-9:   LR = {lrs[0]:.6f}")
    print(f"   Epochs 10-19: LR = {lrs[10]:.6f}")
    print(f"   Epochs 20-29: LR = {lrs[20]:.6f}")
    print()

    # 2. Exponential Decay
    print("2. EXPONENTIAL DECAY SCHEDULER:")
    print("-" * 40)

    exp_scheduler = manager.create_scheduler(
        "exp",
        SchedulerType.EXPONENTIAL,
        config=config,
        gamma=0.9
    )

    lrs = [manager.step("exp") for _ in range(30)]

    print(f"   Epoch 0:  LR = {lrs[0]:.6f}")
    print(f"   Epoch 10: LR = {lrs[9]:.6f}")
    print(f"   Epoch 20: LR = {lrs[19]:.6f}")
    print()

    # 3. Cosine Annealing
    print("3. COSINE ANNEALING SCHEDULER:")
    print("-" * 40)

    cos_scheduler = manager.create_scheduler(
        "cosine",
        SchedulerType.COSINE,
        config=config
    )

    lrs = [manager.step("cosine") for _ in range(50)]

    print(f"   Epoch 0:  LR = {lrs[0]:.6f}")
    print(f"   Epoch 25: LR = {lrs[24]:.6f}")
    print(f"   Epoch 49: LR = {lrs[48]:.6f}")
    print()

    # 4. Cyclic Learning Rate
    print("4. CYCLIC LEARNING RATE:")
    print("-" * 40)

    cyclic_config = SchedulerConfig(
        base_lr=0.001,
        max_lr=0.1,
        total_epochs=100
    )

    cyclic_scheduler = manager.create_scheduler(
        "cyclic",
        SchedulerType.CYCLIC,
        config=cyclic_config,
        step_size_up=5,
        mode=CyclicMode.TRIANGULAR
    )

    lrs = [manager.step("cyclic") for _ in range(20)]

    print(f"   Epochs 0-4 (up):   {[f'{lr:.4f}' for lr in lrs[0:5]]}")
    print(f"   Epochs 5-9 (down): {[f'{lr:.4f}' for lr in lrs[5:10]]}")
    print()

    # 5. One-Cycle Policy
    print("5. ONE-CYCLE POLICY:")
    print("-" * 40)

    onecycle_config = SchedulerConfig(
        base_lr=0.001,
        max_lr=0.1,
        total_epochs=50
    )

    onecycle_scheduler = manager.create_scheduler(
        "onecycle",
        SchedulerType.ONECYCLE,
        config=onecycle_config,
        pct_start=0.3
    )

    lrs = [manager.step("onecycle") for _ in range(50)]

    print(f"   Epoch 0:  LR = {lrs[0]:.6f} (warmup)")
    print(f"   Epoch 15: LR = {lrs[14]:.6f} (peak)")
    print(f"   Epoch 49: LR = {lrs[48]:.6f} (final)")
    print()

    # 6. Linear Decay
    print("6. LINEAR DECAY SCHEDULER:")
    print("-" * 40)

    linear_scheduler = manager.create_scheduler(
        "linear",
        SchedulerType.LINEAR,
        config=config
    )

    lrs = [manager.step("linear") for _ in range(50)]

    print(f"   Epoch 0:  LR = {lrs[0]:.6f}")
    print(f"   Epoch 25: LR = {lrs[24]:.6f}")
    print(f"   Epoch 49: LR = {lrs[48]:.6f}")
    print()

    # 7. Multi-Step Decay
    print("7. MULTI-STEP DECAY:")
    print("-" * 40)

    multistep_scheduler = manager.create_scheduler(
        "multistep",
        SchedulerType.MULTISTEP,
        config=config,
        milestones=[10, 30, 45],
        gamma=0.1
    )

    lrs = [manager.step("multistep") for _ in range(50)]

    print(f"   Epochs 0-9:   LR = {lrs[0]:.6f}")
    print(f"   Epochs 10-29: LR = {lrs[15]:.6f}")
    print(f"   Epochs 30-44: LR = {lrs[35]:.6f}")
    print(f"   Epochs 45+:   LR = {lrs[48]:.8f}")
    print()

    # 8. Reduce on Plateau
    print("8. REDUCE ON PLATEAU:")
    print("-" * 40)

    plateau_scheduler = manager.create_scheduler(
        "plateau",
        SchedulerType.REDUCE_ON_PLATEAU,
        config=config,
        factor=0.5,
        patience=3
    )

    metrics = [1.0, 0.9, 0.85, 0.85, 0.85, 0.85, 0.8, 0.8, 0.8, 0.8]

    for i, metric in enumerate(metrics):
        lr = plateau_scheduler.step_with_metric(metric)
        print(f"   Epoch {i}: metric={metric:.2f}, LR={lr:.6f}")
    print()

    # 9. History
    print("9. SCHEDULER HISTORY:")
    print("-" * 40)

    history = manager.get_history("cosine")

    print(f"   Total steps: {history.total_steps}")
    print(f"   Min LR: {history.min_lr:.6f}")
    print(f"   Max LR: {history.max_lr:.6f}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Scheduler Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
