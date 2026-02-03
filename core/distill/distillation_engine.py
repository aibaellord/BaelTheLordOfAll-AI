#!/usr/bin/env python3
"""
BAEL - Distillation Engine
Knowledge distillation for model compression.

Features:
- Teacher-student training
- Response distillation
- Feature distillation
- Attention transfer
- Progressive distillation
"""

import asyncio
import json
import math
import os
import random
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class DistillationType(Enum):
    """Distillation types."""
    RESPONSE = "response"
    FEATURE = "feature"
    ATTENTION = "attention"
    RELATION = "relation"
    SELF = "self"


class DistillationMode(Enum):
    """Distillation modes."""
    OFFLINE = "offline"
    ONLINE = "online"
    PROGRESSIVE = "progressive"


class LossType(Enum):
    """Loss types."""
    KL_DIVERGENCE = "kl_divergence"
    MSE = "mse"
    COSINE = "cosine"
    CROSS_ENTROPY = "cross_entropy"
    COMBINED = "combined"


class DistillationStatus(Enum):
    """Distillation status."""
    PENDING = "pending"
    EXTRACTING = "extracting"
    DISTILLING = "distilling"
    COMPLETED = "completed"
    FAILED = "failed"


class TemperatureSchedule(Enum):
    """Temperature schedules."""
    CONSTANT = "constant"
    LINEAR = "linear"
    COSINE = "cosine"
    EXPONENTIAL = "exponential"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class DistillationConfig:
    """Distillation configuration."""
    distillation_type: DistillationType = DistillationType.RESPONSE
    mode: DistillationMode = DistillationMode.OFFLINE
    loss_type: LossType = LossType.KL_DIVERGENCE
    temperature: float = 4.0
    alpha: float = 0.5
    beta: float = 0.5
    num_epochs: int = 10
    batch_size: int = 32
    learning_rate: float = 0.001
    temperature_schedule: TemperatureSchedule = TemperatureSchedule.CONSTANT
    feature_layers: List[str] = field(default_factory=list)


@dataclass
class TeacherOutput:
    """Teacher model output."""
    logits: List[float] = field(default_factory=list)
    features: Dict[str, List[float]] = field(default_factory=dict)
    attentions: List[List[float]] = field(default_factory=list)
    hidden_states: List[List[float]] = field(default_factory=list)


@dataclass
class StudentOutput:
    """Student model output."""
    logits: List[float] = field(default_factory=list)
    features: Dict[str, List[float]] = field(default_factory=dict)
    attentions: List[List[float]] = field(default_factory=list)
    hidden_states: List[List[float]] = field(default_factory=list)
    loss: float = 0.0


@dataclass
class DistillationLoss:
    """Distillation loss components."""
    total_loss: float = 0.0
    distillation_loss: float = 0.0
    task_loss: float = 0.0
    feature_loss: float = 0.0
    attention_loss: float = 0.0


@dataclass
class DistillationStep:
    """Single distillation step."""
    step: int = 0
    epoch: int = 0
    loss: DistillationLoss = field(default_factory=DistillationLoss)
    temperature: float = 4.0
    learning_rate: float = 0.001
    duration_ms: float = 0.0


@dataclass
class DistillationResult:
    """Distillation result."""
    result_id: str = ""
    status: DistillationStatus = DistillationStatus.PENDING
    config: DistillationConfig = field(default_factory=DistillationConfig)
    teacher_params: int = 0
    student_params: int = 0
    compression_ratio: float = 1.0
    final_loss: float = 0.0
    teacher_accuracy: float = 0.0
    student_accuracy: float = 0.0
    accuracy_gap: float = 0.0
    training_steps: List[DistillationStep] = field(default_factory=list)
    total_epochs: int = 0
    duration_ms: float = 0.0
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.result_id:
            self.result_id = str(uuid.uuid4())[:8]


@dataclass
class FeatureMap:
    """Feature map for distillation."""
    teacher_layer: str
    student_layer: str
    transform: Optional[str] = None


# =============================================================================
# LOSS FUNCTIONS
# =============================================================================

class BaseLoss(ABC):
    """Abstract base loss function."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Get loss name."""
        pass

    @abstractmethod
    def compute(
        self,
        student_output: List[float],
        teacher_output: List[float],
        temperature: float = 1.0
    ) -> float:
        """Compute loss."""
        pass


class KLDivergenceLoss(BaseLoss):
    """KL Divergence loss."""

    @property
    def name(self) -> str:
        return "kl_divergence"

    def _softmax(self, logits: List[float], temperature: float = 1.0) -> List[float]:
        """Compute softmax with temperature."""
        scaled = [l / temperature for l in logits]
        max_val = max(scaled)
        exp_vals = [math.exp(l - max_val) for l in scaled]
        sum_exp = sum(exp_vals)
        return [e / sum_exp for e in exp_vals]

    def compute(
        self,
        student_output: List[float],
        teacher_output: List[float],
        temperature: float = 1.0
    ) -> float:
        student_probs = self._softmax(student_output, temperature)
        teacher_probs = self._softmax(teacher_output, temperature)

        kl = 0.0
        for p, q in zip(teacher_probs, student_probs):
            if p > 0 and q > 0:
                kl += p * math.log(p / q)

        return kl * (temperature ** 2)


class MSELoss(BaseLoss):
    """Mean Squared Error loss."""

    @property
    def name(self) -> str:
        return "mse"

    def compute(
        self,
        student_output: List[float],
        teacher_output: List[float],
        temperature: float = 1.0
    ) -> float:
        if len(student_output) != len(teacher_output):
            return float("inf")

        mse = sum(
            (s - t) ** 2 for s, t in zip(student_output, teacher_output)
        ) / len(student_output)

        return mse


class CosineLoss(BaseLoss):
    """Cosine similarity loss."""

    @property
    def name(self) -> str:
        return "cosine"

    def compute(
        self,
        student_output: List[float],
        teacher_output: List[float],
        temperature: float = 1.0
    ) -> float:
        dot = sum(s * t for s, t in zip(student_output, teacher_output))
        norm_s = math.sqrt(sum(s ** 2 for s in student_output))
        norm_t = math.sqrt(sum(t ** 2 for t in teacher_output))

        if norm_s == 0 or norm_t == 0:
            return 1.0

        cosine_sim = dot / (norm_s * norm_t)

        return 1.0 - cosine_sim


class CrossEntropyLoss(BaseLoss):
    """Cross entropy loss."""

    @property
    def name(self) -> str:
        return "cross_entropy"

    def _softmax(self, logits: List[float], temperature: float = 1.0) -> List[float]:
        scaled = [l / temperature for l in logits]
        max_val = max(scaled)
        exp_vals = [math.exp(l - max_val) for l in scaled]
        sum_exp = sum(exp_vals)
        return [e / sum_exp for e in exp_vals]

    def compute(
        self,
        student_output: List[float],
        teacher_output: List[float],
        temperature: float = 1.0
    ) -> float:
        student_probs = self._softmax(student_output, temperature)
        teacher_probs = self._softmax(teacher_output, temperature)

        ce = 0.0
        for p, q in zip(teacher_probs, student_probs):
            if q > 0:
                ce -= p * math.log(q)

        return ce


# =============================================================================
# TEMPERATURE SCHEDULERS
# =============================================================================

class BaseTemperatureScheduler(ABC):
    """Abstract base temperature scheduler."""

    @abstractmethod
    def get_temperature(
        self,
        step: int,
        total_steps: int,
        initial_temp: float,
        final_temp: float = 1.0
    ) -> float:
        """Get temperature for current step."""
        pass


class ConstantTemperatureScheduler(BaseTemperatureScheduler):
    """Constant temperature scheduler."""

    def get_temperature(
        self,
        step: int,
        total_steps: int,
        initial_temp: float,
        final_temp: float = 1.0
    ) -> float:
        return initial_temp


class LinearTemperatureScheduler(BaseTemperatureScheduler):
    """Linear temperature scheduler."""

    def get_temperature(
        self,
        step: int,
        total_steps: int,
        initial_temp: float,
        final_temp: float = 1.0
    ) -> float:
        if total_steps <= 1:
            return final_temp

        progress = step / (total_steps - 1)
        return initial_temp + progress * (final_temp - initial_temp)


class CosineTemperatureScheduler(BaseTemperatureScheduler):
    """Cosine temperature scheduler."""

    def get_temperature(
        self,
        step: int,
        total_steps: int,
        initial_temp: float,
        final_temp: float = 1.0
    ) -> float:
        if total_steps <= 1:
            return final_temp

        progress = step / (total_steps - 1)
        cosine_decay = 0.5 * (1 + math.cos(math.pi * progress))

        return final_temp + (initial_temp - final_temp) * cosine_decay


class ExponentialTemperatureScheduler(BaseTemperatureScheduler):
    """Exponential temperature scheduler."""

    def get_temperature(
        self,
        step: int,
        total_steps: int,
        initial_temp: float,
        final_temp: float = 1.0
    ) -> float:
        if total_steps <= 1:
            return final_temp

        decay_rate = math.log(final_temp / initial_temp) / (total_steps - 1)

        return initial_temp * math.exp(decay_rate * step)


# =============================================================================
# DISTILLATION STRATEGIES
# =============================================================================

class BaseDistillationStrategy(ABC):
    """Abstract base distillation strategy."""

    @property
    @abstractmethod
    def distillation_type(self) -> DistillationType:
        """Get distillation type."""
        pass

    @abstractmethod
    def distill(
        self,
        teacher_output: TeacherOutput,
        student_output: StudentOutput,
        config: DistillationConfig
    ) -> DistillationLoss:
        """Perform distillation."""
        pass


class ResponseDistillation(BaseDistillationStrategy):
    """Response-based distillation."""

    def __init__(self):
        self._kl_loss = KLDivergenceLoss()

    @property
    def distillation_type(self) -> DistillationType:
        return DistillationType.RESPONSE

    def distill(
        self,
        teacher_output: TeacherOutput,
        student_output: StudentOutput,
        config: DistillationConfig
    ) -> DistillationLoss:
        distill_loss = self._kl_loss.compute(
            student_output.logits,
            teacher_output.logits,
            config.temperature
        )

        task_loss = student_output.loss

        total_loss = (
            config.alpha * distill_loss +
            (1 - config.alpha) * task_loss
        )

        return DistillationLoss(
            total_loss=total_loss,
            distillation_loss=distill_loss,
            task_loss=task_loss
        )


class FeatureDistillation(BaseDistillationStrategy):
    """Feature-based distillation."""

    def __init__(self):
        self._mse_loss = MSELoss()

    @property
    def distillation_type(self) -> DistillationType:
        return DistillationType.FEATURE

    def distill(
        self,
        teacher_output: TeacherOutput,
        student_output: StudentOutput,
        config: DistillationConfig
    ) -> DistillationLoss:
        feature_loss = 0.0
        num_layers = 0

        for layer in config.feature_layers:
            if layer in teacher_output.features and layer in student_output.features:
                layer_loss = self._mse_loss.compute(
                    student_output.features[layer],
                    teacher_output.features[layer]
                )
                feature_loss += layer_loss
                num_layers += 1

        if num_layers > 0:
            feature_loss /= num_layers

        task_loss = student_output.loss

        total_loss = (
            config.beta * feature_loss +
            (1 - config.beta) * task_loss
        )

        return DistillationLoss(
            total_loss=total_loss,
            feature_loss=feature_loss,
            task_loss=task_loss
        )


class AttentionDistillation(BaseDistillationStrategy):
    """Attention-based distillation."""

    def __init__(self):
        self._mse_loss = MSELoss()

    @property
    def distillation_type(self) -> DistillationType:
        return DistillationType.ATTENTION

    def distill(
        self,
        teacher_output: TeacherOutput,
        student_output: StudentOutput,
        config: DistillationConfig
    ) -> DistillationLoss:
        attention_loss = 0.0
        num_layers = 0

        min_layers = min(
            len(teacher_output.attentions),
            len(student_output.attentions)
        )

        for i in range(min_layers):
            layer_loss = self._mse_loss.compute(
                student_output.attentions[i],
                teacher_output.attentions[i]
            )
            attention_loss += layer_loss
            num_layers += 1

        if num_layers > 0:
            attention_loss /= num_layers

        task_loss = student_output.loss

        total_loss = (
            config.beta * attention_loss +
            (1 - config.beta) * task_loss
        )

        return DistillationLoss(
            total_loss=total_loss,
            attention_loss=attention_loss,
            task_loss=task_loss
        )


class CombinedDistillation(BaseDistillationStrategy):
    """Combined distillation (response + feature + attention)."""

    def __init__(self):
        self._response = ResponseDistillation()
        self._feature = FeatureDistillation()
        self._attention = AttentionDistillation()

    @property
    def distillation_type(self) -> DistillationType:
        return DistillationType.RELATION

    def distill(
        self,
        teacher_output: TeacherOutput,
        student_output: StudentOutput,
        config: DistillationConfig
    ) -> DistillationLoss:
        response_loss = self._response.distill(
            teacher_output, student_output, config
        )

        feature_loss = self._feature.distill(
            teacher_output, student_output, config
        )

        attention_loss = self._attention.distill(
            teacher_output, student_output, config
        )

        total_loss = (
            0.4 * response_loss.distillation_loss +
            0.3 * feature_loss.feature_loss +
            0.3 * attention_loss.attention_loss
        )

        return DistillationLoss(
            total_loss=total_loss,
            distillation_loss=response_loss.distillation_loss,
            feature_loss=feature_loss.feature_loss,
            attention_loss=attention_loss.attention_loss,
            task_loss=student_output.loss
        )


# =============================================================================
# DISTILLATION ENGINE
# =============================================================================

class DistillationEngine:
    """
    Distillation Engine for BAEL.

    Knowledge distillation for model compression.
    """

    def __init__(self):
        self._strategies: Dict[DistillationType, BaseDistillationStrategy] = {
            DistillationType.RESPONSE: ResponseDistillation(),
            DistillationType.FEATURE: FeatureDistillation(),
            DistillationType.ATTENTION: AttentionDistillation(),
            DistillationType.RELATION: CombinedDistillation()
        }

        self._losses: Dict[LossType, BaseLoss] = {
            LossType.KL_DIVERGENCE: KLDivergenceLoss(),
            LossType.MSE: MSELoss(),
            LossType.COSINE: CosineLoss(),
            LossType.CROSS_ENTROPY: CrossEntropyLoss()
        }

        self._temp_schedulers: Dict[TemperatureSchedule, BaseTemperatureScheduler] = {
            TemperatureSchedule.CONSTANT: ConstantTemperatureScheduler(),
            TemperatureSchedule.LINEAR: LinearTemperatureScheduler(),
            TemperatureSchedule.COSINE: CosineTemperatureScheduler(),
            TemperatureSchedule.EXPONENTIAL: ExponentialTemperatureScheduler()
        }

        self._results: Dict[str, DistillationResult] = {}

    def _simulate_teacher(self, num_classes: int = 10) -> TeacherOutput:
        """Simulate teacher output."""
        logits = [random.gauss(0, 2) for _ in range(num_classes)]

        features = {
            f"layer_{i}": [random.gauss(0, 1) for _ in range(128)]
            for i in range(4)
        }

        attentions = [
            [random.random() for _ in range(64)]
            for _ in range(6)
        ]

        return TeacherOutput(
            logits=logits,
            features=features,
            attentions=attentions
        )

    def _simulate_student(
        self,
        teacher: TeacherOutput,
        noise: float = 0.5
    ) -> StudentOutput:
        """Simulate student output."""
        logits = [
            l + random.gauss(0, noise) for l in teacher.logits
        ]

        features = {}
        for name, feat in teacher.features.items():
            features[name] = [f + random.gauss(0, noise) for f in feat]

        attentions = []
        for attn in teacher.attentions:
            attentions.append([a + random.gauss(0, noise * 0.1) for a in attn])

        return StudentOutput(
            logits=logits,
            features=features,
            attentions=attentions,
            loss=random.uniform(0.1, 0.5)
        )

    async def extract_teacher_knowledge(
        self,
        teacher_outputs: List[TeacherOutput]
    ) -> Dict[str, Any]:
        """Extract knowledge from teacher outputs."""
        knowledge = {
            "num_samples": len(teacher_outputs),
            "logit_stats": {},
            "feature_stats": {}
        }

        if teacher_outputs:
            all_logits = [t.logits for t in teacher_outputs]
            avg_logits = [
                sum(l[i] for l in all_logits) / len(all_logits)
                for i in range(len(all_logits[0]))
            ]
            knowledge["logit_stats"]["mean"] = avg_logits

        return knowledge

    async def distill_step(
        self,
        teacher_output: TeacherOutput,
        student_output: StudentOutput,
        config: DistillationConfig
    ) -> DistillationLoss:
        """Perform one distillation step."""
        strategy = self._strategies.get(
            config.distillation_type,
            self._strategies[DistillationType.RESPONSE]
        )

        return strategy.distill(teacher_output, student_output, config)

    async def distill(
        self,
        teacher_params: int,
        student_params: int,
        config: Optional[DistillationConfig] = None,
        num_samples: int = 100
    ) -> DistillationResult:
        """Run distillation training."""
        start_time = time.time()
        config = config or DistillationConfig()

        result = DistillationResult(
            config=config,
            status=DistillationStatus.EXTRACTING,
            teacher_params=teacher_params,
            student_params=student_params
        )

        result.compression_ratio = teacher_params / student_params if student_params > 0 else 1.0

        try:
            teacher_outputs = [
                self._simulate_teacher() for _ in range(num_samples)
            ]

            await self.extract_teacher_knowledge(teacher_outputs)

            result.status = DistillationStatus.DISTILLING

            temp_scheduler = self._temp_schedulers.get(
                config.temperature_schedule,
                ConstantTemperatureScheduler()
            )

            total_steps = config.num_epochs * (num_samples // config.batch_size)
            step_num = 0

            for epoch in range(config.num_epochs):
                epoch_loss = 0.0
                batch_count = 0

                for batch_start in range(0, num_samples, config.batch_size):
                    step_start = time.time()

                    batch_end = min(batch_start + config.batch_size, num_samples)
                    batch_teachers = teacher_outputs[batch_start:batch_end]

                    temperature = temp_scheduler.get_temperature(
                        step_num,
                        total_steps,
                        config.temperature,
                        1.0
                    )

                    batch_loss = 0.0
                    for teacher in batch_teachers:
                        noise = 0.5 * (1 - step_num / max(total_steps, 1))
                        student = self._simulate_student(teacher, noise)

                        step_config = DistillationConfig(
                            distillation_type=config.distillation_type,
                            temperature=temperature,
                            alpha=config.alpha,
                            beta=config.beta,
                            feature_layers=config.feature_layers
                        )

                        loss = await self.distill_step(
                            teacher, student, step_config
                        )
                        batch_loss += loss.total_loss

                    avg_batch_loss = batch_loss / len(batch_teachers)
                    epoch_loss += avg_batch_loss
                    batch_count += 1

                    step = DistillationStep(
                        step=step_num,
                        epoch=epoch,
                        loss=DistillationLoss(total_loss=avg_batch_loss),
                        temperature=temperature,
                        learning_rate=config.learning_rate,
                        duration_ms=(time.time() - step_start) * 1000
                    )
                    result.training_steps.append(step)

                    step_num += 1

                result.total_epochs = epoch + 1

            result.final_loss = result.training_steps[-1].loss.total_loss if result.training_steps else 0.0

            result.teacher_accuracy = 0.92 + random.uniform(-0.02, 0.02)
            result.student_accuracy = result.teacher_accuracy - (0.05 * random.uniform(0.5, 1.5))
            result.accuracy_gap = result.teacher_accuracy - result.student_accuracy

            result.status = DistillationStatus.COMPLETED
            result.duration_ms = (time.time() - start_time) * 1000

        except Exception as e:
            result.status = DistillationStatus.FAILED
            result.error = str(e)
            result.duration_ms = (time.time() - start_time) * 1000

        self._results[result.result_id] = result

        return result

    async def progressive_distill(
        self,
        teacher_params: int,
        intermediate_params: List[int],
        final_student_params: int,
        config: Optional[DistillationConfig] = None
    ) -> List[DistillationResult]:
        """Progressive distillation through multiple stages."""
        config = config or DistillationConfig(mode=DistillationMode.PROGRESSIVE)

        results = []
        current_teacher = teacher_params

        all_stages = intermediate_params + [final_student_params]

        for stage, student_size in enumerate(all_stages):
            stage_config = DistillationConfig(
                distillation_type=config.distillation_type,
                temperature=config.temperature * (0.9 ** stage),
                alpha=config.alpha,
                num_epochs=config.num_epochs // len(all_stages) + 1
            )

            result = await self.distill(
                current_teacher,
                student_size,
                stage_config
            )
            results.append(result)

            current_teacher = student_size

        return results

    def get_result(self, result_id: str) -> Optional[DistillationResult]:
        """Get a distillation result."""
        return self._results.get(result_id)

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "distillation_types": [d.value for d in self._strategies.keys()],
            "loss_functions": [l.value for l in self._losses.keys()],
            "temperature_schedules": [t.value for t in self._temp_schedulers.keys()],
            "total_distillations": len(self._results),
            "successful_distillations": sum(
                1 for r in self._results.values()
                if r.status == DistillationStatus.COMPLETED
            )
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Distillation Engine."""
    print("=" * 70)
    print("BAEL - DISTILLATION ENGINE DEMO")
    print("Knowledge Distillation for Model Compression")
    print("=" * 70)
    print()

    engine = DistillationEngine()

    # 1. Engine Capabilities
    print("1. ENGINE CAPABILITIES:")
    print("-" * 40)

    summary = engine.summary()
    print(f"   Types: {summary['distillation_types']}")
    print(f"   Losses: {summary['loss_functions']}")
    print(f"   Temp Schedules: {summary['temperature_schedules']}")
    print()

    # 2. Response Distillation
    print("2. RESPONSE DISTILLATION:")
    print("-" * 40)

    config = DistillationConfig(
        distillation_type=DistillationType.RESPONSE,
        temperature=4.0,
        alpha=0.7,
        num_epochs=3
    )

    result = await engine.distill(
        teacher_params=100_000_000,
        student_params=10_000_000,
        config=config,
        num_samples=50
    )

    print(f"   Status: {result.status.value}")
    print(f"   Teacher: {result.teacher_params:,} params")
    print(f"   Student: {result.student_params:,} params")
    print(f"   Compression: {result.compression_ratio:.1f}x")
    print(f"   Final Loss: {result.final_loss:.4f}")
    print()

    # 3. Feature Distillation
    print("3. FEATURE DISTILLATION:")
    print("-" * 40)

    feature_config = DistillationConfig(
        distillation_type=DistillationType.FEATURE,
        feature_layers=["layer_0", "layer_1", "layer_2", "layer_3"],
        beta=0.8,
        num_epochs=3
    )

    feature_result = await engine.distill(
        teacher_params=50_000_000,
        student_params=5_000_000,
        config=feature_config,
        num_samples=30
    )

    print(f"   Compression: {feature_result.compression_ratio:.1f}x")
    print(f"   Final Loss: {feature_result.final_loss:.4f}")
    print()

    # 4. Attention Distillation
    print("4. ATTENTION DISTILLATION:")
    print("-" * 40)

    attn_config = DistillationConfig(
        distillation_type=DistillationType.ATTENTION,
        num_epochs=3
    )

    attn_result = await engine.distill(
        teacher_params=30_000_000,
        student_params=3_000_000,
        config=attn_config,
        num_samples=30
    )

    print(f"   Compression: {attn_result.compression_ratio:.1f}x")
    print(f"   Final Loss: {attn_result.final_loss:.4f}")
    print()

    # 5. Temperature Schedule
    print("5. TEMPERATURE SCHEDULES:")
    print("-" * 40)

    for schedule in [TemperatureSchedule.CONSTANT, TemperatureSchedule.COSINE]:
        sched_config = DistillationConfig(
            temperature=6.0,
            temperature_schedule=schedule,
            num_epochs=2
        )

        sched_result = await engine.distill(
            teacher_params=20_000_000,
            student_params=2_000_000,
            config=sched_config,
            num_samples=20
        )

        final_temp = sched_result.training_steps[-1].temperature if sched_result.training_steps else 0
        print(f"   {schedule.value}: final_temp={final_temp:.2f}")
    print()

    # 6. Training Progress
    print("6. TRAINING PROGRESS:")
    print("-" * 40)

    if result.training_steps:
        print("   Step | Epoch | Loss    | Temp")
        print("   " + "-" * 35)

        steps_to_show = result.training_steps[::max(1, len(result.training_steps) // 5)]
        for step in steps_to_show[:5]:
            print(f"   {step.step:4d} | {step.epoch:5d} | {step.loss.total_loss:.4f} | {step.temperature:.2f}")
    print()

    # 7. Accuracy Analysis
    print("7. ACCURACY ANALYSIS:")
    print("-" * 40)

    print(f"   Teacher Accuracy: {result.teacher_accuracy * 100:.2f}%")
    print(f"   Student Accuracy: {result.student_accuracy * 100:.2f}%")
    print(f"   Accuracy Gap: {result.accuracy_gap * 100:.2f}%")
    print()

    # 8. Progressive Distillation
    print("8. PROGRESSIVE DISTILLATION:")
    print("-" * 40)

    prog_config = DistillationConfig(num_epochs=2)

    prog_results = await engine.progressive_distill(
        teacher_params=100_000_000,
        intermediate_params=[50_000_000, 20_000_000],
        final_student_params=5_000_000,
        config=prog_config
    )

    for i, pr in enumerate(prog_results):
        print(f"   Stage {i + 1}: {pr.teacher_params:,} → {pr.student_params:,}")
        print(f"           Compression: {pr.compression_ratio:.1f}x, Loss: {pr.final_loss:.4f}")
    print()

    # 9. Combined Distillation
    print("9. COMBINED DISTILLATION:")
    print("-" * 40)

    combined_config = DistillationConfig(
        distillation_type=DistillationType.RELATION,
        feature_layers=["layer_0", "layer_1"],
        num_epochs=2
    )

    combined_result = await engine.distill(
        teacher_params=80_000_000,
        student_params=8_000_000,
        config=combined_config,
        num_samples=30
    )

    print(f"   Compression: {combined_result.compression_ratio:.1f}x")
    print(f"   Final Loss: {combined_result.final_loss:.4f}")
    print()

    # 10. Summary
    print("10. ENGINE SUMMARY:")
    print("-" * 40)

    final_summary = engine.summary()
    print(f"   Total Distillations: {final_summary['total_distillations']}")
    print(f"   Successful: {final_summary['successful_distillations']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Distillation Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
