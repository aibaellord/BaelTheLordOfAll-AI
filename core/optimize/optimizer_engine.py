#!/usr/bin/env python3
"""
BAEL - Optimizer Engine
Advanced optimization algorithms for AI agents.

Features:
- SGD with momentum
- Adam optimizer
- RMSprop
- AdaGrad
- Learning rate scheduling
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
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class OptimizerType(Enum):
    """Optimizer types."""
    SGD = "sgd"
    MOMENTUM = "momentum"
    NESTEROV = "nesterov"
    ADAGRAD = "adagrad"
    RMSPROP = "rmsprop"
    ADAM = "adam"
    ADAMW = "adamw"
    AMSGRAD = "amsgrad"


class SchedulerType(Enum):
    """Learning rate scheduler types."""
    CONSTANT = "constant"
    STEP = "step"
    EXPONENTIAL = "exponential"
    COSINE = "cosine"
    LINEAR = "linear"
    WARMUP = "warmup"


class RegularizationType(Enum):
    """Regularization types."""
    NONE = "none"
    L1 = "l1"
    L2 = "l2"
    ELASTIC = "elastic"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Parameter:
    """A parameter to optimize."""
    param_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    value: float = 0.0
    gradient: float = 0.0
    name: str = ""


@dataclass
class ParameterGroup:
    """A group of parameters."""
    group_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parameters: List[Parameter] = field(default_factory=list)
    learning_rate: float = 0.001


@dataclass
class OptimizerState:
    """State for an optimizer."""
    step: int = 0
    momentum_buffers: Dict[str, float] = field(default_factory=dict)
    velocity_buffers: Dict[str, float] = field(default_factory=dict)
    exp_avg: Dict[str, float] = field(default_factory=dict)
    exp_avg_sq: Dict[str, float] = field(default_factory=dict)
    max_exp_avg_sq: Dict[str, float] = field(default_factory=dict)


@dataclass
class OptimizationResult:
    """Result of optimization step."""
    updated_values: Dict[str, float] = field(default_factory=dict)
    learning_rate: float = 0.0
    step: int = 0


# =============================================================================
# OPTIMIZER BASE
# =============================================================================

class Optimizer(ABC):
    """Abstract base optimizer."""

    @abstractmethod
    def step(self, parameters: List[Parameter]) -> None:
        """Perform optimization step."""
        pass

    @abstractmethod
    def zero_grad(self, parameters: List[Parameter]) -> None:
        """Zero gradients."""
        pass


# =============================================================================
# SGD OPTIMIZER
# =============================================================================

class SGDOptimizer(Optimizer):
    """Stochastic Gradient Descent optimizer."""

    def __init__(
        self,
        learning_rate: float = 0.01,
        momentum: float = 0.0,
        nesterov: bool = False,
        weight_decay: float = 0.0
    ):
        self._lr = learning_rate
        self._momentum = momentum
        self._nesterov = nesterov
        self._weight_decay = weight_decay
        self._state = OptimizerState()

    def step(self, parameters: List[Parameter]) -> None:
        """Perform SGD step."""
        for param in parameters:
            grad = param.gradient

            if self._weight_decay > 0:
                grad += self._weight_decay * param.value

            if self._momentum > 0:
                if param.param_id not in self._state.momentum_buffers:
                    self._state.momentum_buffers[param.param_id] = grad
                else:
                    buf = self._state.momentum_buffers[param.param_id]
                    buf = self._momentum * buf + grad
                    self._state.momentum_buffers[param.param_id] = buf

                if self._nesterov:
                    grad = grad + self._momentum * buf
                else:
                    grad = buf

            param.value -= self._lr * grad

        self._state.step += 1

    def zero_grad(self, parameters: List[Parameter]) -> None:
        """Zero gradients."""
        for param in parameters:
            param.gradient = 0.0


# =============================================================================
# ADAGRAD OPTIMIZER
# =============================================================================

class AdaGradOptimizer(Optimizer):
    """AdaGrad optimizer."""

    def __init__(
        self,
        learning_rate: float = 0.01,
        epsilon: float = 1e-10,
        weight_decay: float = 0.0
    ):
        self._lr = learning_rate
        self._epsilon = epsilon
        self._weight_decay = weight_decay
        self._state = OptimizerState()

    def step(self, parameters: List[Parameter]) -> None:
        """Perform AdaGrad step."""
        for param in parameters:
            grad = param.gradient

            if self._weight_decay > 0:
                grad += self._weight_decay * param.value

            if param.param_id not in self._state.exp_avg_sq:
                self._state.exp_avg_sq[param.param_id] = 0.0

            self._state.exp_avg_sq[param.param_id] += grad ** 2

            std = math.sqrt(self._state.exp_avg_sq[param.param_id]) + self._epsilon
            param.value -= self._lr * grad / std

        self._state.step += 1

    def zero_grad(self, parameters: List[Parameter]) -> None:
        """Zero gradients."""
        for param in parameters:
            param.gradient = 0.0


# =============================================================================
# RMSPROP OPTIMIZER
# =============================================================================

class RMSpropOptimizer(Optimizer):
    """RMSprop optimizer."""

    def __init__(
        self,
        learning_rate: float = 0.01,
        alpha: float = 0.99,
        epsilon: float = 1e-8,
        momentum: float = 0.0,
        weight_decay: float = 0.0
    ):
        self._lr = learning_rate
        self._alpha = alpha
        self._epsilon = epsilon
        self._momentum = momentum
        self._weight_decay = weight_decay
        self._state = OptimizerState()

    def step(self, parameters: List[Parameter]) -> None:
        """Perform RMSprop step."""
        for param in parameters:
            grad = param.gradient

            if self._weight_decay > 0:
                grad += self._weight_decay * param.value

            if param.param_id not in self._state.exp_avg_sq:
                self._state.exp_avg_sq[param.param_id] = 0.0

            self._state.exp_avg_sq[param.param_id] = (
                self._alpha * self._state.exp_avg_sq[param.param_id] +
                (1 - self._alpha) * grad ** 2
            )

            avg = math.sqrt(self._state.exp_avg_sq[param.param_id]) + self._epsilon

            if self._momentum > 0:
                if param.param_id not in self._state.momentum_buffers:
                    self._state.momentum_buffers[param.param_id] = 0.0

                buf = self._state.momentum_buffers[param.param_id]
                buf = self._momentum * buf + grad / avg
                self._state.momentum_buffers[param.param_id] = buf
                param.value -= self._lr * buf
            else:
                param.value -= self._lr * grad / avg

        self._state.step += 1

    def zero_grad(self, parameters: List[Parameter]) -> None:
        """Zero gradients."""
        for param in parameters:
            param.gradient = 0.0


# =============================================================================
# ADAM OPTIMIZER
# =============================================================================

class AdamOptimizer(Optimizer):
    """Adam optimizer."""

    def __init__(
        self,
        learning_rate: float = 0.001,
        beta1: float = 0.9,
        beta2: float = 0.999,
        epsilon: float = 1e-8,
        weight_decay: float = 0.0,
        amsgrad: bool = False
    ):
        self._lr = learning_rate
        self._beta1 = beta1
        self._beta2 = beta2
        self._epsilon = epsilon
        self._weight_decay = weight_decay
        self._amsgrad = amsgrad
        self._state = OptimizerState()

    def step(self, parameters: List[Parameter]) -> None:
        """Perform Adam step."""
        self._state.step += 1

        for param in parameters:
            grad = param.gradient

            if self._weight_decay > 0:
                grad += self._weight_decay * param.value

            if param.param_id not in self._state.exp_avg:
                self._state.exp_avg[param.param_id] = 0.0
                self._state.exp_avg_sq[param.param_id] = 0.0
                if self._amsgrad:
                    self._state.max_exp_avg_sq[param.param_id] = 0.0

            self._state.exp_avg[param.param_id] = (
                self._beta1 * self._state.exp_avg[param.param_id] +
                (1 - self._beta1) * grad
            )

            self._state.exp_avg_sq[param.param_id] = (
                self._beta2 * self._state.exp_avg_sq[param.param_id] +
                (1 - self._beta2) * grad ** 2
            )

            bias_correction1 = 1 - self._beta1 ** self._state.step
            bias_correction2 = 1 - self._beta2 ** self._state.step

            m_hat = self._state.exp_avg[param.param_id] / bias_correction1
            v_hat = self._state.exp_avg_sq[param.param_id] / bias_correction2

            if self._amsgrad:
                self._state.max_exp_avg_sq[param.param_id] = max(
                    self._state.max_exp_avg_sq[param.param_id],
                    v_hat
                )
                v_hat = self._state.max_exp_avg_sq[param.param_id]

            param.value -= self._lr * m_hat / (math.sqrt(v_hat) + self._epsilon)

    def zero_grad(self, parameters: List[Parameter]) -> None:
        """Zero gradients."""
        for param in parameters:
            param.gradient = 0.0


# =============================================================================
# ADAMW OPTIMIZER
# =============================================================================

class AdamWOptimizer(Optimizer):
    """AdamW optimizer (Adam with decoupled weight decay)."""

    def __init__(
        self,
        learning_rate: float = 0.001,
        beta1: float = 0.9,
        beta2: float = 0.999,
        epsilon: float = 1e-8,
        weight_decay: float = 0.01
    ):
        self._lr = learning_rate
        self._beta1 = beta1
        self._beta2 = beta2
        self._epsilon = epsilon
        self._weight_decay = weight_decay
        self._state = OptimizerState()

    def step(self, parameters: List[Parameter]) -> None:
        """Perform AdamW step."""
        self._state.step += 1

        for param in parameters:
            param.value -= self._lr * self._weight_decay * param.value

            grad = param.gradient

            if param.param_id not in self._state.exp_avg:
                self._state.exp_avg[param.param_id] = 0.0
                self._state.exp_avg_sq[param.param_id] = 0.0

            self._state.exp_avg[param.param_id] = (
                self._beta1 * self._state.exp_avg[param.param_id] +
                (1 - self._beta1) * grad
            )

            self._state.exp_avg_sq[param.param_id] = (
                self._beta2 * self._state.exp_avg_sq[param.param_id] +
                (1 - self._beta2) * grad ** 2
            )

            bias_correction1 = 1 - self._beta1 ** self._state.step
            bias_correction2 = 1 - self._beta2 ** self._state.step

            m_hat = self._state.exp_avg[param.param_id] / bias_correction1
            v_hat = self._state.exp_avg_sq[param.param_id] / bias_correction2

            param.value -= self._lr * m_hat / (math.sqrt(v_hat) + self._epsilon)

    def zero_grad(self, parameters: List[Parameter]) -> None:
        """Zero gradients."""
        for param in parameters:
            param.gradient = 0.0


# =============================================================================
# LEARNING RATE SCHEDULER
# =============================================================================

class LRScheduler(ABC):
    """Abstract learning rate scheduler."""

    @abstractmethod
    def get_lr(self, step: int) -> float:
        """Get learning rate for step."""
        pass


class StepScheduler(LRScheduler):
    """Step learning rate scheduler."""

    def __init__(
        self,
        initial_lr: float,
        step_size: int,
        gamma: float = 0.1
    ):
        self._initial_lr = initial_lr
        self._step_size = step_size
        self._gamma = gamma

    def get_lr(self, step: int) -> float:
        """Get learning rate."""
        return self._initial_lr * (self._gamma ** (step // self._step_size))


class ExponentialScheduler(LRScheduler):
    """Exponential learning rate scheduler."""

    def __init__(self, initial_lr: float, gamma: float = 0.99):
        self._initial_lr = initial_lr
        self._gamma = gamma

    def get_lr(self, step: int) -> float:
        """Get learning rate."""
        return self._initial_lr * (self._gamma ** step)


class CosineScheduler(LRScheduler):
    """Cosine annealing learning rate scheduler."""

    def __init__(
        self,
        initial_lr: float,
        total_steps: int,
        min_lr: float = 0.0
    ):
        self._initial_lr = initial_lr
        self._total_steps = total_steps
        self._min_lr = min_lr

    def get_lr(self, step: int) -> float:
        """Get learning rate."""
        if step >= self._total_steps:
            return self._min_lr

        return self._min_lr + 0.5 * (self._initial_lr - self._min_lr) * (
            1 + math.cos(math.pi * step / self._total_steps)
        )


class WarmupScheduler(LRScheduler):
    """Warmup learning rate scheduler."""

    def __init__(
        self,
        initial_lr: float,
        warmup_steps: int,
        warmup_start: float = 0.0
    ):
        self._initial_lr = initial_lr
        self._warmup_steps = warmup_steps
        self._warmup_start = warmup_start

    def get_lr(self, step: int) -> float:
        """Get learning rate."""
        if step >= self._warmup_steps:
            return self._initial_lr

        return self._warmup_start + (self._initial_lr - self._warmup_start) * (
            step / self._warmup_steps
        )


class LinearScheduler(LRScheduler):
    """Linear learning rate scheduler."""

    def __init__(
        self,
        initial_lr: float,
        total_steps: int,
        end_lr: float = 0.0
    ):
        self._initial_lr = initial_lr
        self._total_steps = total_steps
        self._end_lr = end_lr

    def get_lr(self, step: int) -> float:
        """Get learning rate."""
        if step >= self._total_steps:
            return self._end_lr

        return self._initial_lr + (self._end_lr - self._initial_lr) * (
            step / self._total_steps
        )


# =============================================================================
# REGULARIZER
# =============================================================================

class Regularizer:
    """Compute regularization loss."""

    @staticmethod
    def l1(parameters: List[Parameter], lambda_: float = 0.01) -> float:
        """L1 regularization."""
        return lambda_ * sum(abs(p.value) for p in parameters)

    @staticmethod
    def l2(parameters: List[Parameter], lambda_: float = 0.01) -> float:
        """L2 regularization."""
        return 0.5 * lambda_ * sum(p.value ** 2 for p in parameters)

    @staticmethod
    def elastic(
        parameters: List[Parameter],
        lambda_: float = 0.01,
        alpha: float = 0.5
    ) -> float:
        """Elastic net regularization."""
        l1 = sum(abs(p.value) for p in parameters)
        l2 = sum(p.value ** 2 for p in parameters)
        return lambda_ * (alpha * l1 + 0.5 * (1 - alpha) * l2)


# =============================================================================
# OPTIMIZER ENGINE
# =============================================================================

class OptimizerEngine:
    """
    Optimizer Engine for BAEL.

    Advanced optimization algorithms for AI agents.
    """

    def __init__(self):
        self._optimizers: Dict[str, Optimizer] = {}
        self._schedulers: Dict[str, LRScheduler] = {}

    def create_sgd(
        self,
        name: str,
        learning_rate: float = 0.01,
        momentum: float = 0.0,
        nesterov: bool = False,
        weight_decay: float = 0.0
    ) -> SGDOptimizer:
        """Create SGD optimizer."""
        optimizer = SGDOptimizer(learning_rate, momentum, nesterov, weight_decay)
        self._optimizers[name] = optimizer
        return optimizer

    def create_adam(
        self,
        name: str,
        learning_rate: float = 0.001,
        beta1: float = 0.9,
        beta2: float = 0.999,
        epsilon: float = 1e-8,
        weight_decay: float = 0.0,
        amsgrad: bool = False
    ) -> AdamOptimizer:
        """Create Adam optimizer."""
        optimizer = AdamOptimizer(
            learning_rate, beta1, beta2, epsilon, weight_decay, amsgrad
        )
        self._optimizers[name] = optimizer
        return optimizer

    def create_adamw(
        self,
        name: str,
        learning_rate: float = 0.001,
        beta1: float = 0.9,
        beta2: float = 0.999,
        epsilon: float = 1e-8,
        weight_decay: float = 0.01
    ) -> AdamWOptimizer:
        """Create AdamW optimizer."""
        optimizer = AdamWOptimizer(
            learning_rate, beta1, beta2, epsilon, weight_decay
        )
        self._optimizers[name] = optimizer
        return optimizer

    def create_rmsprop(
        self,
        name: str,
        learning_rate: float = 0.01,
        alpha: float = 0.99,
        epsilon: float = 1e-8,
        momentum: float = 0.0,
        weight_decay: float = 0.0
    ) -> RMSpropOptimizer:
        """Create RMSprop optimizer."""
        optimizer = RMSpropOptimizer(
            learning_rate, alpha, epsilon, momentum, weight_decay
        )
        self._optimizers[name] = optimizer
        return optimizer

    def create_adagrad(
        self,
        name: str,
        learning_rate: float = 0.01,
        epsilon: float = 1e-10,
        weight_decay: float = 0.0
    ) -> AdaGradOptimizer:
        """Create AdaGrad optimizer."""
        optimizer = AdaGradOptimizer(learning_rate, epsilon, weight_decay)
        self._optimizers[name] = optimizer
        return optimizer

    def create_step_scheduler(
        self,
        name: str,
        initial_lr: float,
        step_size: int,
        gamma: float = 0.1
    ) -> StepScheduler:
        """Create step scheduler."""
        scheduler = StepScheduler(initial_lr, step_size, gamma)
        self._schedulers[name] = scheduler
        return scheduler

    def create_cosine_scheduler(
        self,
        name: str,
        initial_lr: float,
        total_steps: int,
        min_lr: float = 0.0
    ) -> CosineScheduler:
        """Create cosine scheduler."""
        scheduler = CosineScheduler(initial_lr, total_steps, min_lr)
        self._schedulers[name] = scheduler
        return scheduler

    def create_warmup_scheduler(
        self,
        name: str,
        initial_lr: float,
        warmup_steps: int,
        warmup_start: float = 0.0
    ) -> WarmupScheduler:
        """Create warmup scheduler."""
        scheduler = WarmupScheduler(initial_lr, warmup_steps, warmup_start)
        self._schedulers[name] = scheduler
        return scheduler

    def get_optimizer(self, name: str) -> Optional[Optimizer]:
        """Get optimizer by name."""
        return self._optimizers.get(name)

    def get_scheduler(self, name: str) -> Optional[LRScheduler]:
        """Get scheduler by name."""
        return self._schedulers.get(name)

    def compute_regularization(
        self,
        parameters: List[Parameter],
        reg_type: RegularizationType = RegularizationType.L2,
        lambda_: float = 0.01
    ) -> float:
        """Compute regularization loss."""
        if reg_type == RegularizationType.L1:
            return Regularizer.l1(parameters, lambda_)
        elif reg_type == RegularizationType.L2:
            return Regularizer.l2(parameters, lambda_)
        elif reg_type == RegularizationType.ELASTIC:
            return Regularizer.elastic(parameters, lambda_)
        return 0.0


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Optimizer Engine."""
    print("=" * 70)
    print("BAEL - OPTIMIZER ENGINE DEMO")
    print("Advanced Optimization Algorithms for AI Agents")
    print("=" * 70)
    print()

    engine = OptimizerEngine()

    def create_params() -> List[Parameter]:
        return [
            Parameter(value=random.gauss(0, 1), gradient=random.gauss(0, 1))
            for _ in range(5)
        ]

    # 1. SGD Optimizer
    print("1. SGD OPTIMIZER:")
    print("-" * 40)

    sgd = engine.create_sgd("sgd", learning_rate=0.1, momentum=0.9)
    params = create_params()

    print(f"   Initial values: {[f'{p.value:.3f}' for p in params]}")

    for _ in range(3):
        for p in params:
            p.gradient = random.gauss(0, 1)
        sgd.step(params)

    print(f"   After 3 steps: {[f'{p.value:.3f}' for p in params]}")
    print()

    # 2. Adam Optimizer
    print("2. ADAM OPTIMIZER:")
    print("-" * 40)

    adam = engine.create_adam("adam", learning_rate=0.01)
    params = create_params()

    print(f"   Initial values: {[f'{p.value:.3f}' for p in params]}")

    for _ in range(5):
        for p in params:
            p.gradient = random.gauss(0, 1)
        adam.step(params)

    print(f"   After 5 steps: {[f'{p.value:.3f}' for p in params]}")
    print()

    # 3. AdamW Optimizer
    print("3. ADAMW OPTIMIZER:")
    print("-" * 40)

    adamw = engine.create_adamw("adamw", learning_rate=0.01, weight_decay=0.01)
    params = create_params()

    print(f"   Initial values: {[f'{p.value:.3f}' for p in params]}")

    for _ in range(5):
        for p in params:
            p.gradient = random.gauss(0, 1)
        adamw.step(params)

    print(f"   After 5 steps: {[f'{p.value:.3f}' for p in params]}")
    print()

    # 4. Learning Rate Schedulers
    print("4. LEARNING RATE SCHEDULERS:")
    print("-" * 40)

    step_sched = engine.create_step_scheduler("step", 0.1, 10, 0.1)
    cosine_sched = engine.create_cosine_scheduler("cosine", 0.1, 100)
    warmup_sched = engine.create_warmup_scheduler("warmup", 0.1, 10)

    steps = [0, 5, 10, 20, 50, 100]

    print("   Step | StepLR | CosineLR | WarmupLR")
    for step in steps:
        step_lr = step_sched.get_lr(step)
        cosine_lr = cosine_sched.get_lr(step)
        warmup_lr = warmup_sched.get_lr(step)
        print(f"   {step:4d} | {step_lr:.4f} | {cosine_lr:.4f}   | {warmup_lr:.4f}")
    print()

    # 5. Regularization
    print("5. REGULARIZATION:")
    print("-" * 40)

    params = create_params()

    l1_loss = engine.compute_regularization(params, RegularizationType.L1, 0.01)
    l2_loss = engine.compute_regularization(params, RegularizationType.L2, 0.01)
    elastic_loss = engine.compute_regularization(params, RegularizationType.ELASTIC, 0.01)

    print(f"   L1 regularization: {l1_loss:.6f}")
    print(f"   L2 regularization: {l2_loss:.6f}")
    print(f"   Elastic net: {elastic_loss:.6f}")
    print()

    # 6. RMSprop and AdaGrad
    print("6. RMSPROP AND ADAGRAD:")
    print("-" * 40)

    rmsprop = engine.create_rmsprop("rmsprop", learning_rate=0.01)
    adagrad = engine.create_adagrad("adagrad", learning_rate=0.01)

    params_rms = create_params()
    params_ada = create_params()

    print(f"   RMSprop initial: {[f'{p.value:.3f}' for p in params_rms]}")
    print(f"   AdaGrad initial: {[f'{p.value:.3f}' for p in params_ada]}")

    for _ in range(5):
        for p in params_rms:
            p.gradient = random.gauss(0, 1)
        for p in params_ada:
            p.gradient = random.gauss(0, 1)
        rmsprop.step(params_rms)
        adagrad.step(params_ada)

    print(f"   RMSprop after 5: {[f'{p.value:.3f}' for p in params_rms]}")
    print(f"   AdaGrad after 5: {[f'{p.value:.3f}' for p in params_ada]}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Optimizer Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
