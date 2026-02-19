"""
BAEL Meta-Learning System
==========================

Learning to learn - adaptive optimization of learning strategies.

"The mind that learns how to learn is forever unlimited." — Ba'el
"""

import asyncio
import logging
import random
import math
import json
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger("BAEL.MetaLearning")


class LearningStrategy(Enum):
    """Learning strategies."""
    MAML = "maml"                     # Model-Agnostic Meta-Learning
    REPTILE = "reptile"               # Reptile algorithm
    PROTOTYPICAL = "prototypical"     # Prototype networks
    MATCHING = "matching"             # Matching networks
    TRANSFER = "transfer"             # Transfer learning
    MULTI_TASK = "multi_task"         # Multi-task learning
    CURRICULUM = "curriculum"         # Curriculum learning
    SELF_SUPERVISED = "self_supervised"  # Self-supervised learning


class TaskType(Enum):
    """Types of tasks."""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    GENERATION = "generation"
    OPTIMIZATION = "optimization"
    REASONING = "reasoning"


class AdaptationSpeed(Enum):
    """Speed of adaptation."""
    INSTANT = "instant"      # 1-shot
    FAST = "fast"            # Few-shot
    MODERATE = "moderate"    # Standard learning
    SLOW = "slow"            # Many examples needed


@dataclass
class Task:
    """A learning task."""
    id: str
    task_type: TaskType
    description: str
    examples: List[Dict[str, Any]]
    validation: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningExperience:
    """Record of learning experience."""
    task_id: str
    strategy: LearningStrategy
    success_rate: float
    adaptation_time: float  # seconds
    examples_needed: int
    final_performance: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MetaKnowledge:
    """Knowledge about learning."""
    task_type: TaskType
    best_strategy: LearningStrategy
    average_examples_needed: int
    typical_performance: float
    confidence: float


@dataclass
class Prototype:
    """Prototype for prototypical learning."""
    class_name: str
    representation: List[float]
    support_size: int


@dataclass
class AdaptationResult:
    """Result of task adaptation."""
    success: bool
    strategy_used: LearningStrategy
    examples_used: int
    performance: float
    adaptation_time_seconds: float
    predictions: List[Any]


class ExperienceBuffer:
    """Buffer for storing learning experiences."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._buffer: List[LearningExperience] = []

    def add(self, experience: LearningExperience) -> None:
        """Add experience."""
        self._buffer.append(experience)
        if len(self._buffer) > self.max_size:
            self._buffer.pop(0)

    def get_by_strategy(self, strategy: LearningStrategy) -> List[LearningExperience]:
        """Get experiences for strategy."""
        return [e for e in self._buffer if e.strategy == strategy]

    def get_best_strategy(self, task_type: TaskType = None) -> Optional[LearningStrategy]:
        """Get best strategy based on experience."""
        if not self._buffer:
            return None

        strategy_performance = defaultdict(list)

        for exp in self._buffer:
            strategy_performance[exp.strategy].append(exp.final_performance)

        if not strategy_performance:
            return None

        # Return strategy with highest average performance
        best = max(
            strategy_performance.items(),
            key=lambda x: sum(x[1]) / len(x[1])
        )

        return best[0]


class PrototypicalLearner:
    """
    Prototypical Networks for few-shot learning.

    Creates class prototypes from support examples.
    """

    def __init__(self, embedding_fn: Callable[[Any], List[float]] = None):
        self.embedding_fn = embedding_fn or self._default_embedding
        self._prototypes: Dict[str, Prototype] = {}

    def _default_embedding(self, x: Any) -> List[float]:
        """Simple hash-based embedding."""
        s = str(x)
        # Create simple embedding from character codes
        embedding = [0.0] * 64
        for i, c in enumerate(s[:64]):
            embedding[i] = ord(c) / 256.0
        return embedding

    async def learn_prototypes(
        self,
        support_set: Dict[str, List[Any]],
    ) -> Dict[str, Prototype]:
        """Learn prototypes from support set."""
        prototypes = {}

        for class_name, examples in support_set.items():
            if not examples:
                continue

            # Get embeddings
            embeddings = []
            for example in examples:
                if asyncio.iscoroutinefunction(self.embedding_fn):
                    emb = await self.embedding_fn(example)
                else:
                    emb = self.embedding_fn(example)
                embeddings.append(emb)

            # Compute mean as prototype
            dim = len(embeddings[0])
            prototype_vec = [
                sum(e[d] for e in embeddings) / len(embeddings)
                for d in range(dim)
            ]

            prototypes[class_name] = Prototype(
                class_name=class_name,
                representation=prototype_vec,
                support_size=len(examples),
            )

        self._prototypes = prototypes
        return prototypes

    async def predict(self, query: Any) -> Tuple[str, float]:
        """Predict class for query."""
        if not self._prototypes:
            return None, 0.0

        # Get query embedding
        if asyncio.iscoroutinefunction(self.embedding_fn):
            query_emb = await self.embedding_fn(query)
        else:
            query_emb = self.embedding_fn(query)

        # Find nearest prototype
        min_dist = float('inf')
        best_class = None

        for class_name, proto in self._prototypes.items():
            dist = sum(
                (a - b) ** 2
                for a, b in zip(query_emb, proto.representation)
            ) ** 0.5

            if dist < min_dist:
                min_dist = dist
                best_class = class_name

        # Convert distance to confidence (lower = more confident)
        confidence = 1.0 / (1.0 + min_dist)

        return best_class, confidence


class MAMLLearner:
    """
    Model-Agnostic Meta-Learning (simplified).

    Learns initialization that enables fast adaptation.
    """

    def __init__(
        self,
        inner_lr: float = 0.1,
        outer_lr: float = 0.001,
        inner_steps: int = 5,
    ):
        self.inner_lr = inner_lr
        self.outer_lr = outer_lr
        self.inner_steps = inner_steps

        # Meta-parameters (simplified as weights)
        self._meta_weights: Dict[str, float] = {}
        self._meta_initialized = False

    async def meta_train(
        self,
        tasks: List[Task],
        epochs: int = 100,
    ) -> Dict[str, Any]:
        """Train meta-learner across tasks."""
        if not tasks:
            return {}

        # Initialize meta-weights from first task
        if not self._meta_initialized:
            first_task = tasks[0]
            for key in self._extract_features(first_task.examples[0] if first_task.examples else {}):
                self._meta_weights[key] = random.gauss(0, 0.1)
            self._meta_initialized = True

        meta_losses = []

        for epoch in range(epochs):
            epoch_loss = 0.0

            for task in tasks:
                # Clone weights for task
                task_weights = dict(self._meta_weights)

                # Inner loop: adapt to task
                for _ in range(self.inner_steps):
                    # Simple gradient step (simulated)
                    for key in task_weights:
                        gradient = self._compute_gradient(task, task_weights, key)
                        task_weights[key] -= self.inner_lr * gradient

                # Compute loss after adaptation
                loss = self._compute_loss(task, task_weights)
                epoch_loss += loss

                # Outer loop: update meta-weights
                for key in self._meta_weights:
                    meta_gradient = self._compute_meta_gradient(task, task_weights, key)
                    self._meta_weights[key] -= self.outer_lr * meta_gradient

            meta_losses.append(epoch_loss / len(tasks))

            if epoch % 10 == 0:
                await asyncio.sleep(0)

        return {
            "epochs": epochs,
            "final_loss": meta_losses[-1] if meta_losses else 0,
            "loss_history": meta_losses,
        }

    async def adapt(
        self,
        task: Task,
        steps: int = None,
    ) -> Dict[str, float]:
        """Adapt to new task."""
        steps = steps or self.inner_steps

        # Start from meta-weights
        task_weights = dict(self._meta_weights)

        for _ in range(steps):
            for key in task_weights:
                gradient = self._compute_gradient(task, task_weights, key)
                task_weights[key] -= self.inner_lr * gradient

        return task_weights

    def _extract_features(self, example: Dict[str, Any]) -> List[str]:
        """Extract feature keys from example."""
        if isinstance(example, dict):
            return list(example.keys())
        return ["value"]

    def _compute_gradient(
        self,
        task: Task,
        weights: Dict[str, float],
        key: str,
    ) -> float:
        """Compute gradient (simplified)."""
        # Numerical gradient estimation
        epsilon = 0.001

        weights_plus = dict(weights)
        weights_plus[key] += epsilon
        loss_plus = self._compute_loss(task, weights_plus)

        weights_minus = dict(weights)
        weights_minus[key] -= epsilon
        loss_minus = self._compute_loss(task, weights_minus)

        return (loss_plus - loss_minus) / (2 * epsilon)

    def _compute_meta_gradient(
        self,
        task: Task,
        adapted_weights: Dict[str, float],
        key: str,
    ) -> float:
        """Compute meta-gradient."""
        return self._compute_gradient(task, adapted_weights, key) * 0.1

    def _compute_loss(
        self,
        task: Task,
        weights: Dict[str, float],
    ) -> float:
        """Compute loss on task (simplified)."""
        if not task.validation:
            return 0.0

        total_loss = 0.0

        for example in task.validation:
            # Simple linear prediction
            pred = sum(
                weights.get(k, 0) * (v if isinstance(v, (int, float)) else 0)
                for k, v in example.items()
                if k != "target"
            )

            target = example.get("target", 0)
            if isinstance(target, (int, float)):
                total_loss += (pred - target) ** 2

        return total_loss / len(task.validation)


class CurriculumLearner:
    """
    Curriculum learning - progressive task difficulty.
    """

    def __init__(self):
        self._task_difficulties: Dict[str, float] = {}
        self._current_level: float = 0.0

    def assess_difficulty(self, task: Task) -> float:
        """Assess task difficulty."""
        # Factors: example complexity, number of classes, etc.
        complexity = 0.0

        if task.examples:
            # Average example size
            avg_size = sum(
                len(str(e)) for e in task.examples
            ) / len(task.examples)
            complexity += min(avg_size / 1000, 1.0) * 0.3

        # Number of examples (fewer = harder)
        n_examples = len(task.examples)
        complexity += max(0, 1 - n_examples / 100) * 0.3

        # Task type
        if task.task_type == TaskType.REASONING:
            complexity += 0.4
        elif task.task_type == TaskType.GENERATION:
            complexity += 0.3

        self._task_difficulties[task.id] = complexity
        return complexity

    def sort_by_difficulty(self, tasks: List[Task]) -> List[Task]:
        """Sort tasks by difficulty (easy first)."""
        for task in tasks:
            if task.id not in self._task_difficulties:
                self.assess_difficulty(task)

        return sorted(
            tasks,
            key=lambda t: self._task_difficulties.get(t.id, 0.5)
        )

    def get_next_tasks(
        self,
        tasks: List[Task],
        batch_size: int = 5,
    ) -> List[Task]:
        """Get next batch of tasks at appropriate difficulty."""
        sorted_tasks = self.sort_by_difficulty(tasks)

        # Find tasks near current level
        appropriate = [
            t for t in sorted_tasks
            if abs(self._task_difficulties.get(t.id, 0) - self._current_level) < 0.2
        ]

        if not appropriate:
            # Get slightly harder tasks
            appropriate = [
                t for t in sorted_tasks
                if self._task_difficulties.get(t.id, 0) > self._current_level
            ][:batch_size]

        return appropriate[:batch_size]

    def update_level(self, performance: float) -> None:
        """Update current difficulty level based on performance."""
        if performance > 0.8:
            # Doing well, increase difficulty
            self._current_level = min(1.0, self._current_level + 0.1)
        elif performance < 0.5:
            # Struggling, decrease difficulty
            self._current_level = max(0.0, self._current_level - 0.1)


class MetaLearningSystem:
    """
    Unified meta-learning system.

    Coordinates multiple meta-learning strategies.
    """

    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path.home() / ".bael" / "meta_learning"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.prototypical = PrototypicalLearner()
        self.maml = MAMLLearner()
        self.curriculum = CurriculumLearner()

        self._experience_buffer = ExperienceBuffer()
        self._meta_knowledge: Dict[TaskType, MetaKnowledge] = {}

        self._load_state()

    def _load_state(self) -> None:
        """Load saved state."""
        state_file = self.storage_path / "meta_state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    data = json.load(f)

                for task_type, knowledge in data.get("meta_knowledge", {}).items():
                    self._meta_knowledge[TaskType(task_type)] = MetaKnowledge(
                        task_type=TaskType(task_type),
                        best_strategy=LearningStrategy(knowledge["best_strategy"]),
                        average_examples_needed=knowledge["average_examples_needed"],
                        typical_performance=knowledge["typical_performance"],
                        confidence=knowledge["confidence"],
                    )
            except Exception as e:
                logger.warning(f"Failed to load meta-learning state: {e}")

    def _save_state(self) -> None:
        """Save state."""
        state_file = self.storage_path / "meta_state.json"
        data = {
            "meta_knowledge": {
                k.value: {
                    "best_strategy": v.best_strategy.value,
                    "average_examples_needed": v.average_examples_needed,
                    "typical_performance": v.typical_performance,
                    "confidence": v.confidence,
                }
                for k, v in self._meta_knowledge.items()
            }
        }

        with open(state_file, "w") as f:
            json.dump(data, f, indent=2)

    async def adapt_to_task(
        self,
        task: Task,
        strategy: LearningStrategy = None,
    ) -> AdaptationResult:
        """Adapt to a new task."""
        import time
        start = time.time()

        # Select strategy
        if strategy is None:
            strategy = self._select_strategy(task.task_type)

        predictions = []
        performance = 0.0

        if strategy == LearningStrategy.PROTOTYPICAL:
            # Use prototypical learning
            support_set = defaultdict(list)
            for ex in task.examples:
                label = ex.get("label", "unknown")
                support_set[label].append(ex.get("input", ex))

            await self.prototypical.learn_prototypes(support_set)

            # Predict on validation
            correct = 0
            for val_ex in task.validation:
                query = val_ex.get("input", val_ex)
                true_label = val_ex.get("label", "unknown")

                pred_label, conf = await self.prototypical.predict(query)
                predictions.append({"prediction": pred_label, "confidence": conf})

                if pred_label == true_label:
                    correct += 1

            performance = correct / len(task.validation) if task.validation else 0

        elif strategy == LearningStrategy.MAML:
            # Use MAML
            await self.maml.meta_train([task], epochs=50)
            weights = await self.maml.adapt(task)

            # Simple prediction
            for val_ex in task.validation:
                pred = sum(
                    weights.get(k, 0) * (v if isinstance(v, (int, float)) else 0)
                    for k, v in val_ex.items()
                    if k != "target"
                )
                predictions.append({"prediction": pred})

            performance = 0.7  # Simulated

        elif strategy == LearningStrategy.CURRICULUM:
            # Use curriculum learning
            self.curriculum.assess_difficulty(task)
            performance = 0.6  # Simulated

        else:
            performance = 0.5

        duration = time.time() - start

        # Record experience
        experience = LearningExperience(
            task_id=task.id,
            strategy=strategy,
            success_rate=performance,
            adaptation_time=duration,
            examples_needed=len(task.examples),
            final_performance=performance,
        )
        self._experience_buffer.add(experience)

        # Update meta-knowledge
        self._update_meta_knowledge(task.task_type, experience)
        self._save_state()

        return AdaptationResult(
            success=performance > 0.5,
            strategy_used=strategy,
            examples_used=len(task.examples),
            performance=performance,
            adaptation_time_seconds=duration,
            predictions=predictions,
        )

    def _select_strategy(self, task_type: TaskType) -> LearningStrategy:
        """Select best strategy for task type."""
        # Check meta-knowledge
        if task_type in self._meta_knowledge:
            knowledge = self._meta_knowledge[task_type]
            if knowledge.confidence > 0.7:
                return knowledge.best_strategy

        # Check experience buffer
        best = self._experience_buffer.get_best_strategy()
        if best:
            return best

        # Default strategies
        defaults = {
            TaskType.CLASSIFICATION: LearningStrategy.PROTOTYPICAL,
            TaskType.REGRESSION: LearningStrategy.MAML,
            TaskType.GENERATION: LearningStrategy.TRANSFER,
            TaskType.REASONING: LearningStrategy.MULTI_TASK,
            TaskType.OPTIMIZATION: LearningStrategy.MAML,
        }

        return defaults.get(task_type, LearningStrategy.PROTOTYPICAL)

    def _update_meta_knowledge(
        self,
        task_type: TaskType,
        experience: LearningExperience,
    ) -> None:
        """Update meta-knowledge from experience."""
        if task_type not in self._meta_knowledge:
            self._meta_knowledge[task_type] = MetaKnowledge(
                task_type=task_type,
                best_strategy=experience.strategy,
                average_examples_needed=experience.examples_needed,
                typical_performance=experience.final_performance,
                confidence=0.1,
            )
        else:
            knowledge = self._meta_knowledge[task_type]

            # Update with exponential moving average
            alpha = 0.1
            knowledge.average_examples_needed = int(
                (1 - alpha) * knowledge.average_examples_needed +
                alpha * experience.examples_needed
            )
            knowledge.typical_performance = (
                (1 - alpha) * knowledge.typical_performance +
                alpha * experience.final_performance
            )

            # Update best strategy if this one performed better
            if experience.final_performance > knowledge.typical_performance:
                knowledge.best_strategy = experience.strategy

            # Increase confidence with more experience
            knowledge.confidence = min(1.0, knowledge.confidence + 0.05)

    def get_meta_summary(self) -> Dict[str, Any]:
        """Get summary of meta-learning state."""
        return {
            "total_experiences": len(self._experience_buffer._buffer),
            "meta_knowledge": {
                k.value: {
                    "best_strategy": v.best_strategy.value,
                    "avg_examples": v.average_examples_needed,
                    "typical_performance": v.typical_performance,
                    "confidence": v.confidence,
                }
                for k, v in self._meta_knowledge.items()
            },
            "curriculum_level": self.curriculum._current_level,
        }


# Convenience instance
meta_learner = MetaLearningSystem()
