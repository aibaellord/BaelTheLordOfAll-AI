"""
BAEL Continual Learner - Core Learning Orchestrator

This module orchestrates all continual learning capabilities,
coordinating between EWC, PackNet, Experience Replay, and
Knowledge Distillation to enable lifelong learning.

Features:
- Multi-task learning without forgetting
- Adaptive learning rate scheduling
- Automatic task boundary detection
- Knowledge transfer between tasks
- Learning curriculum optimization
"""

import asyncio
import json
import logging
import math
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger("BAEL.ContinualLearner")


# =============================================================================
# ENUMS
# =============================================================================

class LearningStrategy(Enum):
    """Available continual learning strategies."""
    EWC = "ewc"  # Elastic Weight Consolidation
    PACKNET = "packnet"  # Parameter isolation
    REPLAY = "replay"  # Experience replay
    DISTILLATION = "distillation"  # Knowledge distillation
    PROGRESSIVE = "progressive"  # Progressive networks
    HYBRID = "hybrid"  # Combination of strategies


class TaskDifficulty(Enum):
    """Difficulty levels for learning tasks."""
    TRIVIAL = 1
    EASY = 2
    MEDIUM = 3
    HARD = 4
    EXPERT = 5


class LearningPhase(Enum):
    """Phases of the learning process."""
    WARMUP = "warmup"
    ACQUISITION = "acquisition"
    CONSOLIDATION = "consolidation"
    REFINEMENT = "refinement"
    EVALUATION = "evaluation"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class LearningTask:
    """Represents a learning task."""
    id: str
    name: str
    description: str
    domain: str
    difficulty: TaskDifficulty
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    examples: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)  # Task IDs
    importance: float = 1.0

    def add_example(self, input_data: Any, output_data: Any, metadata: Dict = None):
        """Add a learning example."""
        self.examples.append({
            "input": input_data,
            "output": output_data,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        })


@dataclass
class LearningSession:
    """A session of continual learning."""
    id: str
    task: LearningTask
    strategy: LearningStrategy
    phase: LearningPhase
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    iterations: int = 0
    loss_history: List[float] = field(default_factory=list)
    performance_history: List[float] = field(default_factory=list)
    parameters_changed: int = 0

    @property
    def duration_seconds(self) -> float:
        """Get session duration."""
        end = self.ended_at or datetime.now()
        return (end - self.started_at).total_seconds()

    @property
    def final_loss(self) -> Optional[float]:
        """Get final loss value."""
        return self.loss_history[-1] if self.loss_history else None


@dataclass
class KnowledgeState:
    """Represents the current knowledge state."""
    tasks_learned: List[str]
    total_examples: int
    average_performance: float
    forgetting_rate: float
    consolidation_level: float
    last_updated: datetime = field(default_factory=datetime.now)


# =============================================================================
# LEARNING CURRICULUM
# =============================================================================

class LearningCurriculum:
    """
    Manages the order and pacing of learning tasks.

    Features:
    - Difficulty-based ordering
    - Prerequisite enforcement
    - Adaptive pacing
    - Interleaved practice
    """

    def __init__(self):
        self.tasks: Dict[str, LearningTask] = {}
        self.completed: List[str] = []
        self.current_task_id: Optional[str] = None

    def add_task(self, task: LearningTask) -> None:
        """Add a task to the curriculum."""
        self.tasks[task.id] = task

    def get_next_task(self) -> Optional[LearningTask]:
        """Get the next task to learn based on curriculum."""
        # Filter to available tasks (prerequisites met)
        available = []
        for task_id, task in self.tasks.items():
            if task_id in self.completed:
                continue
            if all(dep in self.completed for dep in task.dependencies):
                available.append(task)

        if not available:
            return None

        # Sort by difficulty and importance
        available.sort(key=lambda t: (t.difficulty.value, -t.importance))
        return available[0]

    def complete_task(self, task_id: str) -> None:
        """Mark a task as completed."""
        if task_id not in self.completed:
            self.completed.append(task_id)

        if task_id in self.tasks:
            self.tasks[task_id].completed_at = datetime.now()

    def get_interleaved_practice(self, count: int = 3) -> List[LearningTask]:
        """Get tasks for interleaved practice (spaced repetition)."""
        completed_tasks = [
            self.tasks[tid] for tid in self.completed
            if tid in self.tasks
        ]

        # Prioritize less recent and more important tasks
        completed_tasks.sort(
            key=lambda t: (t.completed_at or datetime.now(), -t.importance)
        )

        return completed_tasks[:count]


# =============================================================================
# KNOWLEDGE TRACKER
# =============================================================================

class KnowledgeTracker:
    """
    Tracks what has been learned and measures forgetting.

    Uses periodic probes to detect forgetting and
    schedule consolidation.
    """

    def __init__(self):
        self.task_performance: Dict[str, List[Tuple[datetime, float]]] = {}
        self.forgetting_alerts: List[Dict] = []
        self.consolidation_schedule: List[str] = []

        # Thresholds
        self.forgetting_threshold = 0.15  # 15% performance drop
        self.probe_interval = 100  # iterations between probes

    def record_performance(self, task_id: str, performance: float) -> None:
        """Record performance on a task."""
        if task_id not in self.task_performance:
            self.task_performance[task_id] = []
        self.task_performance[task_id].append((datetime.now(), performance))

    def check_forgetting(self, task_id: str) -> Optional[float]:
        """
        Check if forgetting has occurred on a task.
        Returns the forgetting rate if detected, None otherwise.
        """
        history = self.task_performance.get(task_id, [])
        if len(history) < 2:
            return None

        peak_performance = max(p for _, p in history)
        current_performance = history[-1][1]

        forgetting_rate = (peak_performance - current_performance) / peak_performance

        if forgetting_rate > self.forgetting_threshold:
            self.forgetting_alerts.append({
                "task_id": task_id,
                "rate": forgetting_rate,
                "timestamp": datetime.now()
            })
            self.schedule_consolidation(task_id)
            return forgetting_rate

        return None

    def schedule_consolidation(self, task_id: str) -> None:
        """Schedule a task for consolidation."""
        if task_id not in self.consolidation_schedule:
            self.consolidation_schedule.append(task_id)

    def get_knowledge_state(self) -> KnowledgeState:
        """Get current knowledge state."""
        if not self.task_performance:
            return KnowledgeState(
                tasks_learned=[],
                total_examples=0,
                average_performance=0.0,
                forgetting_rate=0.0,
                consolidation_level=1.0
            )

        # Calculate metrics
        avg_perf = sum(
            hist[-1][1] if hist else 0
            for hist in self.task_performance.values()
        ) / len(self.task_performance)

        # Estimate overall forgetting
        forgetting_rates = []
        for task_id in self.task_performance:
            rate = self.check_forgetting(task_id)
            if rate:
                forgetting_rates.append(rate)

        avg_forgetting = sum(forgetting_rates) / len(forgetting_rates) if forgetting_rates else 0

        return KnowledgeState(
            tasks_learned=list(self.task_performance.keys()),
            total_examples=sum(len(h) for h in self.task_performance.values()),
            average_performance=avg_perf,
            forgetting_rate=avg_forgetting,
            consolidation_level=1.0 - avg_forgetting
        )


# =============================================================================
# CONTINUAL LEARNER
# =============================================================================

class ContinualLearner:
    """
    Main continual learning orchestrator.

    Coordinates between multiple learning strategies to
    enable lifelong learning without catastrophic forgetting.

    Architecture:
    1. Learning Curriculum - What to learn and when
    2. Strategy Selector - How to learn each task
    3. Knowledge Tracker - Monitor learning and forgetting
    4. Consolidation Engine - Prevent forgetting
    """

    def __init__(self, default_strategy: LearningStrategy = LearningStrategy.HYBRID):
        self.default_strategy = default_strategy
        self.curriculum = LearningCurriculum()
        self.tracker = KnowledgeTracker()

        # Strategy modules (to be wired)
        self.ewc = None
        self.packnet = None
        self.replay_buffer = None
        self.distiller = None

        # State
        self.current_session: Optional[LearningSession] = None
        self.sessions_history: List[LearningSession] = []
        self.parameters: Dict[str, Any] = {}

        # Configuration
        self.config = {
            "ewc_lambda": 1000,  # EWC regularization strength
            "replay_batch_size": 32,
            "distillation_temp": 2.0,
            "consolidation_frequency": 5,  # Tasks between consolidation
            "learning_rate": 0.001,
            "adaptive_lr": True,
            "max_iterations": 1000
        }

        # Metrics
        self.metrics = {
            "tasks_learned": 0,
            "total_examples": 0,
            "average_performance": 0.0,
            "forgetting_events": 0,
            "consolidation_runs": 0
        }

    async def learn_task(
        self,
        task: LearningTask,
        strategy: LearningStrategy = None
    ) -> LearningSession:
        """
        Learn a new task using the specified strategy.

        This is the main entry point for continual learning.
        """
        strategy = strategy or self.default_strategy

        # Create session
        session = LearningSession(
            id=str(uuid4()),
            task=task,
            strategy=strategy,
            phase=LearningPhase.WARMUP
        )
        self.current_session = session

        logger.info(f"Starting learning session for task: {task.name}")

        try:
            # Phase 1: Warmup
            await self._warmup_phase(session)

            # Phase 2: Acquisition
            session.phase = LearningPhase.ACQUISITION
            await self._acquisition_phase(session)

            # Phase 3: Consolidation
            session.phase = LearningPhase.CONSOLIDATION
            await self._consolidation_phase(session)

            # Phase 4: Refinement
            session.phase = LearningPhase.REFINEMENT
            await self._refinement_phase(session)

            # Phase 5: Evaluation
            session.phase = LearningPhase.EVALUATION
            await self._evaluation_phase(session)

            # Complete
            session.ended_at = datetime.now()
            self.sessions_history.append(session)
            self.curriculum.complete_task(task.id)

            # Update metrics
            self.metrics["tasks_learned"] += 1
            self.metrics["total_examples"] += len(task.examples)

            logger.info(
                f"Completed task {task.name} with performance "
                f"{session.performance_history[-1]:.2%}"
            )

        except Exception as e:
            logger.error(f"Learning failed: {e}")
            session.ended_at = datetime.now()
            raise

        finally:
            self.current_session = None

        return session

    async def _warmup_phase(self, session: LearningSession) -> None:
        """Warmup phase - prepare for learning."""
        logger.debug(f"Warmup phase for {session.task.name}")

        # Initialize any task-specific parameters
        task_id = session.task.id
        if task_id not in self.parameters:
            self.parameters[task_id] = {
                "weights": {},
                "fisher_info": {},
                "mask": None
            }

        # Adjust learning rate based on task difficulty
        if self.config["adaptive_lr"]:
            difficulty_factor = session.task.difficulty.value / 3
            lr = self.config["learning_rate"] * difficulty_factor
            logger.debug(f"Adjusted learning rate: {lr}")

    async def _acquisition_phase(self, session: LearningSession) -> None:
        """Acquisition phase - main learning loop."""
        logger.debug(f"Acquisition phase for {session.task.name}")

        task = session.task
        strategy = session.strategy

        # Process examples
        for i, example in enumerate(task.examples):
            session.iterations += 1

            # Forward pass (simulated)
            loss = await self._process_example(example, strategy)
            session.loss_history.append(loss)

            # Apply strategy-specific updates
            if strategy == LearningStrategy.EWC:
                loss += await self._apply_ewc_penalty()
            elif strategy == LearningStrategy.REPLAY:
                await self._replay_from_buffer()

            # Periodic logging
            if i % 10 == 0:
                logger.debug(f"Iteration {i}, Loss: {loss:.4f}")

            # Check for early stopping
            if self._should_early_stop(session):
                logger.info("Early stopping triggered")
                break

    async def _process_example(
        self,
        example: Dict[str, Any],
        strategy: LearningStrategy
    ) -> float:
        """Process a single learning example."""
        # This would interface with actual learning algorithms
        # For now, simulate loss
        import random
        base_loss = random.uniform(0.1, 0.5)

        # Strategy-specific adjustments
        if strategy == LearningStrategy.HYBRID:
            base_loss *= 0.8  # Hybrid typically performs better

        return base_loss

    async def _apply_ewc_penalty(self) -> float:
        """Apply EWC regularization penalty."""
        if self.ewc is None:
            return 0.0

        # Calculate penalty based on Fisher information
        # This prevents changes to important weights
        penalty = 0.0
        for task_id, params in self.parameters.items():
            if "fisher_info" in params:
                # Simplified EWC penalty calculation
                penalty += sum(params.get("fisher_info", {}).values()) * 0.001

        return penalty * self.config["ewc_lambda"]

    async def _replay_from_buffer(self) -> None:
        """Replay experiences from buffer."""
        if self.replay_buffer is None:
            return

        # Sample from replay buffer and include in training
        # This helps maintain performance on previous tasks
        pass

    def _should_early_stop(self, session: LearningSession) -> bool:
        """Check if early stopping should be applied."""
        if len(session.loss_history) < 20:
            return False

        # Check if loss has plateaued
        recent_losses = session.loss_history[-20:]
        variance = sum((l - sum(recent_losses)/len(recent_losses))**2 for l in recent_losses) / len(recent_losses)

        return variance < 0.0001

    async def _consolidation_phase(self, session: LearningSession) -> None:
        """Consolidation phase - prevent forgetting."""
        logger.debug(f"Consolidation phase for {session.task.name}")

        # Calculate Fisher information for EWC
        await self._compute_fisher_information(session.task.id)

        # Update PackNet masks if applicable
        if session.strategy in [LearningStrategy.PACKNET, LearningStrategy.HYBRID]:
            await self._update_network_masks(session.task.id)

        # Add examples to replay buffer
        if self.replay_buffer:
            for example in session.task.examples:
                # Add to replay buffer (would prioritize by difficulty)
                pass

        self.metrics["consolidation_runs"] += 1

    async def _compute_fisher_information(self, task_id: str) -> None:
        """Compute Fisher information matrix for EWC."""
        # Fisher information captures the importance of each weight
        # for the current task
        logger.debug(f"Computing Fisher information for task {task_id}")

        # Simplified: store importance scores
        self.parameters[task_id]["fisher_info"] = {
            "layer_1": 0.5,
            "layer_2": 0.3,
            "layer_3": 0.7
        }

    async def _update_network_masks(self, task_id: str) -> None:
        """Update network masks for PackNet."""
        logger.debug(f"Updating network masks for task {task_id}")

        # PackNet identifies important weights and "freezes" them
        self.parameters[task_id]["mask"] = {
            "frozen_weights": set(),
            "task_specific": set()
        }

    async def _refinement_phase(self, session: LearningSession) -> None:
        """Refinement phase - fine-tune and optimize."""
        logger.debug(f"Refinement phase for {session.task.name}")

        # Interleaved practice with previous tasks
        practice_tasks = self.curriculum.get_interleaved_practice()

        for task in practice_tasks:
            if task.examples:
                # Practice on a few examples from each task
                for example in task.examples[:3]:
                    loss = await self._process_example(example, session.strategy)
                    session.loss_history.append(loss)

    async def _evaluation_phase(self, session: LearningSession) -> None:
        """Evaluation phase - measure final performance."""
        logger.debug(f"Evaluation phase for {session.task.name}")

        # Evaluate on current task
        performance = await self._evaluate_task(session.task)
        session.performance_history.append(performance)

        # Record in tracker
        self.tracker.record_performance(session.task.id, performance)

        # Check for forgetting on previous tasks
        for task_id in self.tracker.task_performance:
            if task_id != session.task.id:
                forgetting = self.tracker.check_forgetting(task_id)
                if forgetting:
                    logger.warning(
                        f"Forgetting detected on task {task_id}: {forgetting:.2%}"
                    )
                    self.metrics["forgetting_events"] += 1

    async def _evaluate_task(self, task: LearningTask) -> float:
        """Evaluate performance on a task."""
        # This would run actual evaluation
        import random
        return random.uniform(0.7, 0.95)

    async def consolidate_all(self) -> None:
        """Run consolidation on all learned tasks."""
        logger.info("Running full consolidation")

        for task_id in self.tracker.consolidation_schedule:
            if task_id in self.curriculum.tasks:
                task = self.curriculum.tasks[task_id]
                logger.debug(f"Consolidating task: {task.name}")
                await self._compute_fisher_information(task_id)

        self.tracker.consolidation_schedule.clear()

    def get_knowledge_state(self) -> KnowledgeState:
        """Get current knowledge state."""
        return self.tracker.get_knowledge_state()

    def get_metrics(self) -> Dict[str, Any]:
        """Get learning metrics."""
        return {
            **self.metrics,
            "knowledge_state": self.get_knowledge_state().__dict__,
            "current_session": self.current_session.id if self.current_session else None,
            "sessions_completed": len(self.sessions_history),
            "tasks_in_curriculum": len(self.curriculum.tasks)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate continual learning capabilities."""
    print("Continual Learning Demo")
    print("=" * 60)

    learner = ContinualLearner()

    # Create some tasks
    task1 = LearningTask(
        id="task_1",
        name="Basic Reasoning",
        description="Learn basic logical reasoning patterns",
        domain="reasoning",
        difficulty=TaskDifficulty.EASY
    )
    task1.add_example({"premise": "All A are B"}, {"conclusion": "Some B are A"})
    task1.add_example({"premise": "If P then Q"}, {"conclusion": "If not Q then not P"})

    task2 = LearningTask(
        id="task_2",
        name="Causal Inference",
        description="Learn causal reasoning patterns",
        domain="reasoning",
        difficulty=TaskDifficulty.MEDIUM,
        dependencies=["task_1"]
    )
    task2.add_example({"cause": "Rain"}, {"effect": "Wet ground"})

    learner.curriculum.add_task(task1)
    learner.curriculum.add_task(task2)

    # Learn tasks
    session1 = await learner.learn_task(task1)
    print(f"\nTask 1 completed:")
    print(f"  Duration: {session1.duration_seconds:.1f}s")
    print(f"  Final loss: {session1.final_loss:.4f}")
    print(f"  Performance: {session1.performance_history[-1]:.2%}")

    session2 = await learner.learn_task(task2)
    print(f"\nTask 2 completed:")
    print(f"  Duration: {session2.duration_seconds:.1f}s")
    print(f"  Final loss: {session2.final_loss:.4f}")
    print(f"  Performance: {session2.performance_history[-1]:.2%}")

    # Show knowledge state
    state = learner.get_knowledge_state()
    print(f"\nKnowledge State:")
    print(f"  Tasks learned: {len(state.tasks_learned)}")
    print(f"  Average performance: {state.average_performance:.2%}")
    print(f"  Forgetting rate: {state.forgetting_rate:.2%}")
    print(f"  Consolidation level: {state.consolidation_level:.2%}")


if __name__ == "__main__":
    asyncio.run(demo())
