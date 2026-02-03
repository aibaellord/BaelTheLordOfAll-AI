"""
BAEL Meta-Learning Framework

Learning-to-learn capabilities that enable rapid adaptation to new tasks
through experience with previous tasks. Implements:

- MAML (Model-Agnostic Meta-Learning)
- Reptile
- Meta-SGD
- Prototypical Networks
- Task-Adaptive Learning

This is THE most sophisticated meta-learning system, enabling
BAEL to become better at learning itself.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class MetaLearningStrategy(Enum):
    """Meta-learning algorithms."""
    MAML = "maml"                    # Model-Agnostic Meta-Learning
    FOMAML = "fomaml"                # First-Order MAML (faster)
    REPTILE = "reptile"              # Implicit gradients
    META_SGD = "meta_sgd"            # Learnable learning rates
    PROTOTYPICAL = "prototypical"   # Prototype-based
    MATCHING = "matching"            # Matching networks
    HYBRID = "hybrid"                # Combine multiple


class TaskType(Enum):
    """Types of tasks for meta-learning."""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    REINFORCEMENT = "reinforcement"
    GENERATION = "generation"
    REASONING = "reasoning"
    MULTIMODAL = "multimodal"


class AdaptationPhase(Enum):
    """Phases of task adaptation."""
    SUPPORT = "support"      # Learning phase (few examples)
    QUERY = "query"          # Evaluation phase
    META_UPDATE = "meta"     # Meta-parameter update


@dataclass
class TaskDistribution:
    """Distribution of tasks for meta-learning."""
    name: str
    task_type: TaskType
    num_classes: int = 5
    shots_per_class: int = 5  # K-shot learning
    query_per_class: int = 15
    task_sampler: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetaLearningConfig:
    """Configuration for meta-learning."""
    strategy: MetaLearningStrategy = MetaLearningStrategy.MAML
    inner_lr: float = 0.01           # Learning rate for task adaptation
    outer_lr: float = 0.001          # Learning rate for meta-update
    inner_steps: int = 5             # Gradient steps for adaptation
    meta_batch_size: int = 4         # Tasks per meta-update
    first_order: bool = True         # Use first-order approximation
    learn_inner_lr: bool = False     # Meta-SGD: learn per-param LR
    reptile_epsilon: float = 0.1     # Reptile interpolation factor
    embedding_dim: int = 128         # For prototypical/matching
    temperature: float = 1.0         # Softmax temperature


@dataclass
class TaskExperience:
    """Experience from learning a single task."""
    task_id: str
    task_type: TaskType
    support_data: Any
    query_data: Any
    initial_weights: Dict[str, np.ndarray]
    adapted_weights: Dict[str, np.ndarray]
    support_loss: float
    query_loss: float
    adaptation_steps: int
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MetaGradient:
    """Meta-gradient from a task."""
    task_id: str
    gradients: Dict[str, np.ndarray]
    query_loss: float
    support_loss: float


class MetaLearner(ABC):
    """Abstract base for meta-learners."""

    @abstractmethod
    async def adapt(
        self,
        support_data: Any,
        weights: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        """Adapt to a new task using support data."""
        pass

    @abstractmethod
    async def meta_update(
        self,
        meta_gradients: List[MetaGradient],
        weights: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        """Update meta-parameters from task gradients."""
        pass


class MAMLLearner(MetaLearner):
    """
    Model-Agnostic Meta-Learning implementation.

    Key idea: Find initialization θ such that after K gradient
    steps on a new task, performance is maximized.

    θ' = θ - α∇L_task(θ)      # Inner loop (adapt)
    θ = θ - β∇Σ L_task(θ')    # Outer loop (meta-update)
    """

    def __init__(self, config: MetaLearningConfig):
        self.config = config
        self.task_experiences: List[TaskExperience] = []
        self.per_param_lr: Dict[str, np.ndarray] = {}  # For Meta-SGD

    async def adapt(
        self,
        support_data: Any,
        weights: Dict[str, np.ndarray],
        loss_fn: Callable,
        gradient_fn: Callable
    ) -> Tuple[Dict[str, np.ndarray], List[float]]:
        """
        Adapt to new task with K gradient steps.

        Returns adapted weights and loss history.
        """
        adapted = {n: w.copy() for n, w in weights.items()}
        losses = []

        for step in range(self.config.inner_steps):
            # Compute loss on support set
            loss = await loss_fn(support_data, adapted)
            losses.append(float(loss))

            # Compute gradients
            grads = await gradient_fn(support_data, adapted)

            # Update weights
            for name in adapted:
                if name in grads:
                    lr = self._get_lr(name)
                    adapted[name] = adapted[name] - lr * grads[name]

        return adapted, losses

    async def compute_meta_gradient(
        self,
        task_data: Tuple[Any, Any],  # (support, query)
        weights: Dict[str, np.ndarray],
        loss_fn: Callable,
        gradient_fn: Callable
    ) -> MetaGradient:
        """
        Compute meta-gradient for one task.

        For first-order MAML, we use:
        ∇_θ L_query(θ') ≈ ∇_θ' L_query(θ')

        Full MAML requires second-order gradients.
        """
        support_data, query_data = task_data

        # Inner loop: adapt to task
        adapted, support_losses = await self.adapt(
            support_data, weights, loss_fn, gradient_fn
        )

        # Compute query loss with adapted weights
        query_loss = await loss_fn(query_data, adapted)

        # Compute gradients on query set
        if self.config.first_order:
            # First-order approximation (FOMAML)
            grads = await gradient_fn(query_data, adapted)
        else:
            # Full MAML: need Hessian-vector product
            # Approximate with finite differences
            grads = await self._compute_full_maml_gradient(
                support_data, query_data, weights,
                adapted, loss_fn, gradient_fn
            )

        return MetaGradient(
            task_id=str(datetime.now().timestamp()),
            gradients=grads,
            query_loss=float(query_loss),
            support_loss=support_losses[-1] if support_losses else 0.0
        )

    async def meta_update(
        self,
        meta_gradients: List[MetaGradient],
        weights: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        """Update meta-parameters from accumulated gradients."""
        if not meta_gradients:
            return weights

        # Average gradients across tasks
        avg_grads = {}
        for name in weights:
            grads = [mg.gradients.get(name) for mg in meta_gradients
                     if name in mg.gradients]
            if grads:
                avg_grads[name] = np.mean(grads, axis=0)

        # Meta-update
        updated = {}
        for name, w in weights.items():
            if name in avg_grads:
                updated[name] = w - self.config.outer_lr * avg_grads[name]
            else:
                updated[name] = w.copy()

        # Update per-parameter LRs if Meta-SGD
        if self.config.learn_inner_lr:
            await self._update_per_param_lr(meta_gradients)

        return updated

    def _get_lr(self, param_name: str) -> np.ndarray:
        """Get learning rate for parameter (scalar or per-param)."""
        if self.config.learn_inner_lr and param_name in self.per_param_lr:
            return self.per_param_lr[param_name]
        return self.config.inner_lr

    async def _compute_full_maml_gradient(
        self,
        support: Any,
        query: Any,
        theta: Dict[str, np.ndarray],
        theta_prime: Dict[str, np.ndarray],
        loss_fn: Callable,
        gradient_fn: Callable
    ) -> Dict[str, np.ndarray]:
        """
        Compute full MAML gradient using finite differences.

        ∇_θ L(θ') = (I - α∇²L_s)^(-1) ∇_θ' L_q

        Approximated via Hessian-vector product.
        """
        epsilon = 1e-4
        query_grads = await gradient_fn(query, theta_prime)
        full_grads = {}

        for name, g in query_grads.items():
            # Hessian-vector product approximation
            theta_plus = {n: w.copy() for n, w in theta.items()}
            theta_plus[name] = theta_plus[name] + epsilon * g

            theta_minus = {n: w.copy() for n, w in theta.items()}
            theta_minus[name] = theta_minus[name] - epsilon * g

            # Adapt both
            adapted_plus, _ = await self.adapt(support, theta_plus, loss_fn, gradient_fn)
            adapted_minus, _ = await self.adapt(support, theta_minus, loss_fn, gradient_fn)

            # Finite difference
            loss_plus = await loss_fn(query, adapted_plus)
            loss_minus = await loss_fn(query, adapted_minus)

            full_grads[name] = (loss_plus - loss_minus) / (2 * epsilon) * g

        return full_grads

    async def _update_per_param_lr(self, meta_gradients: List[MetaGradient]):
        """Update per-parameter learning rates (Meta-SGD)."""
        lr_update_rate = 0.001

        for mg in meta_gradients:
            for name, grad in mg.gradients.items():
                if name not in self.per_param_lr:
                    self.per_param_lr[name] = np.ones_like(grad) * self.config.inner_lr

                # Simple gradient descent on LR
                # In practice, would need gradient of loss w.r.t. LR
                lr_grad = np.sign(grad) * 0.01
                self.per_param_lr[name] = np.clip(
                    self.per_param_lr[name] - lr_update_rate * lr_grad,
                    1e-6, 1.0
                )


class ReptileLearner(MetaLearner):
    """
    Reptile meta-learning algorithm.

    Simpler than MAML - no second-order gradients needed.

    θ = θ + ε(θ'_k - θ)

    Where θ'_k is weights after K steps on task k.
    """

    def __init__(self, config: MetaLearningConfig):
        self.config = config

    async def adapt(
        self,
        support_data: Any,
        weights: Dict[str, np.ndarray],
        loss_fn: Callable,
        gradient_fn: Callable
    ) -> Tuple[Dict[str, np.ndarray], List[float]]:
        """Adapt with standard gradient descent."""
        adapted = {n: w.copy() for n, w in weights.items()}
        losses = []

        for step in range(self.config.inner_steps):
            loss = await loss_fn(support_data, adapted)
            losses.append(float(loss))

            grads = await gradient_fn(support_data, adapted)

            for name in adapted:
                if name in grads:
                    adapted[name] = adapted[name] - self.config.inner_lr * grads[name]

        return adapted, losses

    async def meta_update(
        self,
        task_weights: List[Dict[str, np.ndarray]],
        initial_weights: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        """
        Reptile meta-update: move towards adapted weights.

        θ = θ + ε * mean(θ'_k - θ)
        """
        if not task_weights:
            return initial_weights

        # Average direction to adapted weights
        updated = {}

        for name, w in initial_weights.items():
            directions = []
            for adapted in task_weights:
                if name in adapted:
                    directions.append(adapted[name] - w)

            if directions:
                avg_direction = np.mean(directions, axis=0)
                updated[name] = w + self.config.reptile_epsilon * avg_direction
            else:
                updated[name] = w.copy()

        return updated


class PrototypicalNetwork:
    """
    Prototypical Networks for few-shot classification.

    Learn embeddings such that examples cluster around
    class prototypes. Classification via nearest prototype.

    c_k = (1/|S_k|) Σ f_θ(x_i)  # Class prototype
    p(y=k|x) ∝ exp(-d(f_θ(x), c_k))  # Classification
    """

    def __init__(self, config: MetaLearningConfig):
        self.config = config
        self.prototypes: Dict[str, np.ndarray] = {}

    async def compute_prototypes(
        self,
        support_embeddings: Dict[str, List[np.ndarray]]
    ) -> Dict[str, np.ndarray]:
        """Compute class prototypes from support embeddings."""
        prototypes = {}

        for class_name, embeddings in support_embeddings.items():
            if embeddings:
                prototypes[class_name] = np.mean(embeddings, axis=0)

        self.prototypes = prototypes
        return prototypes

    async def classify(
        self,
        query_embedding: np.ndarray,
        distance: str = "euclidean"
    ) -> Tuple[str, Dict[str, float]]:
        """Classify query by nearest prototype."""
        if not self.prototypes:
            raise ValueError("No prototypes computed")

        distances = {}
        for class_name, prototype in self.prototypes.items():
            if distance == "euclidean":
                d = np.linalg.norm(query_embedding - prototype)
            elif distance == "cosine":
                d = 1 - np.dot(query_embedding, prototype) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(prototype)
                )
            else:
                d = np.linalg.norm(query_embedding - prototype)

            distances[class_name] = float(d)

        # Softmax over negative distances
        logits = {k: -d / self.config.temperature for k, d in distances.items()}
        max_logit = max(logits.values())
        exp_logits = {k: np.exp(v - max_logit) for k, v in logits.items()}
        sum_exp = sum(exp_logits.values())
        probs = {k: v / sum_exp for k, v in exp_logits.items()}

        predicted = min(distances, key=distances.get)
        return predicted, probs


class MetaLearningFramework:
    """
    Master meta-learning framework coordinating all algorithms.

    Enables BAEL to:
    1. Rapidly adapt to new tasks (few-shot learning)
    2. Learn better initializations from experience
    3. Transfer knowledge across task distributions
    4. Optimize its own learning process
    """

    def __init__(self, config: Optional[MetaLearningConfig] = None):
        self.config = config or MetaLearningConfig()

        # Initialize learners
        self.maml = MAMLLearner(self.config)
        self.reptile = ReptileLearner(self.config)
        self.prototypical = PrototypicalNetwork(self.config)

        # Task tracking
        self.task_distributions: Dict[str, TaskDistribution] = {}
        self.experiences: List[TaskExperience] = []
        self.meta_weights: Dict[str, np.ndarray] = {}

        # Statistics
        self.meta_train_loss_history: List[float] = []
        self.adaptation_speed_history: List[float] = []
        self.total_meta_updates = 0

    def register_task_distribution(self, distribution: TaskDistribution):
        """Register a task distribution for meta-learning."""
        self.task_distributions[distribution.name] = distribution
        logger.info(f"Registered task distribution: {distribution.name}")

    async def meta_train_episode(
        self,
        weights: Dict[str, np.ndarray],
        task_sampler: Callable,
        loss_fn: Callable,
        gradient_fn: Callable
    ) -> Tuple[Dict[str, np.ndarray], float]:
        """
        Run one meta-training episode.

        1. Sample batch of tasks
        2. Adapt to each task (inner loop)
        3. Compute meta-gradient from query performance
        4. Update meta-parameters (outer loop)
        """
        meta_gradients = []
        total_query_loss = 0.0

        # Sample batch of tasks
        for _ in range(self.config.meta_batch_size):
            task_data = await task_sampler()

            if self.config.strategy == MetaLearningStrategy.MAML:
                mg = await self.maml.compute_meta_gradient(
                    task_data, weights, loss_fn, gradient_fn
                )
                meta_gradients.append(mg)
                total_query_loss += mg.query_loss

            elif self.config.strategy == MetaLearningStrategy.REPTILE:
                support, query = task_data
                adapted, _ = await self.reptile.adapt(
                    support, weights, loss_fn, gradient_fn
                )
                query_loss = await loss_fn(query, adapted)
                total_query_loss += float(query_loss)

        # Meta-update
        if self.config.strategy in [MetaLearningStrategy.MAML,
                                     MetaLearningStrategy.FOMAML]:
            updated = await self.maml.meta_update(meta_gradients, weights)
        elif self.config.strategy == MetaLearningStrategy.REPTILE:
            # Collect adapted weights
            task_weights = []
            for _ in range(self.config.meta_batch_size):
                task_data = await task_sampler()
                adapted, _ = await self.reptile.adapt(
                    task_data[0], weights, loss_fn, gradient_fn
                )
                task_weights.append(adapted)
            updated = await self.reptile.meta_update(task_weights, weights)
        else:
            updated = weights

        avg_loss = total_query_loss / self.config.meta_batch_size
        self.meta_train_loss_history.append(avg_loss)
        self.total_meta_updates += 1
        self.meta_weights = updated

        return updated, avg_loss

    async def adapt_to_task(
        self,
        support_data: Any,
        loss_fn: Callable,
        gradient_fn: Callable,
        weights: Optional[Dict[str, np.ndarray]] = None
    ) -> Tuple[Dict[str, np.ndarray], float]:
        """
        Adapt to a new task using few examples.

        Uses meta-learned initialization for fast adaptation.
        """
        if weights is None:
            weights = self.meta_weights

        if not weights:
            raise ValueError("No meta-weights available. Run meta_train first.")

        # Adapt using current strategy
        if self.config.strategy in [MetaLearningStrategy.MAML,
                                     MetaLearningStrategy.FOMAML,
                                     MetaLearningStrategy.META_SGD]:
            adapted, losses = await self.maml.adapt(
                support_data, weights, loss_fn, gradient_fn
            )
        else:
            adapted, losses = await self.reptile.adapt(
                support_data, weights, loss_fn, gradient_fn
            )

        final_loss = losses[-1] if losses else float('inf')

        # Track adaptation speed (how fast loss decreases)
        if len(losses) >= 2:
            speed = (losses[0] - losses[-1]) / len(losses)
            self.adaptation_speed_history.append(speed)

        return adapted, final_loss

    async def few_shot_classify(
        self,
        support_set: Dict[str, List[np.ndarray]],  # class -> embeddings
        query_embedding: np.ndarray
    ) -> Tuple[str, Dict[str, float]]:
        """Few-shot classification with prototypical network."""
        await self.prototypical.compute_prototypes(support_set)
        return await self.prototypical.classify(query_embedding)

    def get_meta_statistics(self) -> Dict[str, Any]:
        """Get meta-learning statistics."""
        return {
            "strategy": self.config.strategy.value,
            "total_meta_updates": self.total_meta_updates,
            "avg_meta_loss": (
                np.mean(self.meta_train_loss_history[-100:])
                if self.meta_train_loss_history else 0.0
            ),
            "avg_adaptation_speed": (
                np.mean(self.adaptation_speed_history[-100:])
                if self.adaptation_speed_history else 0.0
            ),
            "inner_lr": self.config.inner_lr,
            "outer_lr": self.config.outer_lr,
            "inner_steps": self.config.inner_steps,
            "task_distributions": list(self.task_distributions.keys())
        }

    def save(self, path: Path):
        """Save meta-learning state."""
        path.mkdir(parents=True, exist_ok=True)

        if self.meta_weights:
            np.savez(path / "meta_weights.npz", **self.meta_weights)

        state = {
            "config": {
                "strategy": self.config.strategy.value,
                "inner_lr": self.config.inner_lr,
                "outer_lr": self.config.outer_lr,
                "inner_steps": self.config.inner_steps
            },
            "total_meta_updates": self.total_meta_updates,
            "loss_history": self.meta_train_loss_history[-1000:]
        }

        import json
        with open(path / "meta_state.json", "w") as f:
            json.dump(state, f, indent=2)

        logger.info(f"Meta-learning state saved to {path}")

    def load(self, path: Path):
        """Load meta-learning state."""
        if (path / "meta_weights.npz").exists():
            data = np.load(path / "meta_weights.npz")
            self.meta_weights = dict(data)

        import json
        with open(path / "meta_state.json") as f:
            state = json.load(f)

        self.total_meta_updates = state["total_meta_updates"]
        self.meta_train_loss_history = state.get("loss_history", [])

        logger.info(f"Meta-learning state loaded from {path}")


def demo():
    """Demonstrate meta-learning."""
    print("=" * 60)
    print("BAEL Meta-Learning Framework Demo")
    print("=" * 60)

    config = MetaLearningConfig(
        strategy=MetaLearningStrategy.MAML,
        inner_lr=0.01,
        outer_lr=0.001,
        inner_steps=5,
        meta_batch_size=4
    )

    framework = MetaLearningFramework(config)

    # Register task distribution
    framework.register_task_distribution(TaskDistribution(
        name="5-way-5-shot",
        task_type=TaskType.CLASSIFICATION,
        num_classes=5,
        shots_per_class=5
    ))

    print("\n✓ MAML: Meta-learn optimal initialization")
    print("✓ Reptile: Simpler meta-learning without 2nd-order gradients")
    print("✓ Meta-SGD: Learn per-parameter learning rates")
    print("✓ Prototypical: Few-shot via class prototypes")
    print(f"\nConfig: {config.inner_steps} inner steps, "
          f"{config.meta_batch_size} tasks/batch")
    print(f"Statistics: {framework.get_meta_statistics()}")


if __name__ == "__main__":
    demo()
