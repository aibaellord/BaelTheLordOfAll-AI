#!/usr/bin/env python3
"""
BAEL - Continual Learning System
Lifelong learning with catastrophic forgetting prevention.

Features:
- Elastic Weight Consolidation (EWC)
- Progressive Neural Networks
- Memory Replay (Experience Replay)
- Knowledge Distillation
- Dynamic Architecture Expansion
- Skill Transfer and Composition
"""

import asyncio
import hashlib
import json
import logging
import math
import random
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class LearningPhase(Enum):
    """Learning phases."""
    INITIAL = "initial"
    TRAINING = "training"
    CONSOLIDATION = "consolidation"
    TRANSFER = "transfer"
    FINE_TUNING = "fine_tuning"


class MemoryType(Enum):
    """Types of learning memory."""
    EPISODIC = "episodic"          # Specific experiences
    SEMANTIC = "semantic"           # General knowledge
    PROCEDURAL = "procedural"       # Skills and procedures
    WORKING = "working"             # Short-term active


class ForgettingStrategy(Enum):
    """Strategies to prevent forgetting."""
    EWC = "elastic_weight_consolidation"
    PROGRESSIVE = "progressive_networks"
    REPLAY = "experience_replay"
    DISTILLATION = "knowledge_distillation"
    EXPANSION = "architecture_expansion"


@dataclass
class Experience:
    """Single learning experience."""
    id: str
    task_id: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    reward: float
    timestamp: datetime = field(default_factory=datetime.now)
    importance: float = 1.0
    retrieval_count: int = 0
    last_retrieved: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Skill:
    """Learned skill or capability."""
    id: str
    name: str
    description: str
    proficiency: float = 0.0  # 0-1
    training_examples: int = 0
    last_practiced: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    transfer_sources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """Learning task definition."""
    id: str
    name: str
    description: str
    domain: str
    difficulty: float = 0.5
    required_skills: List[str] = field(default_factory=list)
    training_data: List[Dict[str, Any]] = field(default_factory=list)
    validation_data: List[Dict[str, Any]] = field(default_factory=list)
    performance_history: List[float] = field(default_factory=list)


@dataclass
class KnowledgeNode:
    """Node in knowledge graph."""
    id: str
    concept: str
    embedding: List[float] = field(default_factory=list)
    importance: float = 1.0
    stability: float = 0.0  # How consolidated
    connections: Dict[str, float] = field(default_factory=dict)  # id -> strength


# =============================================================================
# MEMORY SYSTEMS
# =============================================================================

class ExperienceReplayBuffer:
    """Buffer for experience replay to prevent forgetting."""

    def __init__(
        self,
        capacity: int = 10000,
        priority_exponent: float = 0.6
    ):
        self.capacity = capacity
        self.priority_exponent = priority_exponent
        self.buffer: deque = deque(maxlen=capacity)
        self.priorities: Dict[str, float] = {}

    def add(self, experience: Experience) -> None:
        """Add experience to buffer."""
        self.buffer.append(experience)
        # Initial priority based on importance
        self.priorities[experience.id] = experience.importance

    def sample(
        self,
        batch_size: int,
        strategy: str = "prioritized"
    ) -> List[Experience]:
        """Sample experiences for replay."""
        if not self.buffer:
            return []

        if strategy == "uniform":
            return random.sample(
                list(self.buffer),
                min(batch_size, len(self.buffer))
            )
        elif strategy == "prioritized":
            return self._prioritized_sample(batch_size)
        elif strategy == "reservoir":
            return self._reservoir_sample(batch_size)
        else:
            return list(self.buffer)[:batch_size]

    def _prioritized_sample(self, batch_size: int) -> List[Experience]:
        """Sample with priority weighting."""
        experiences = list(self.buffer)

        # Calculate sampling probabilities
        priorities = [
            self.priorities.get(e.id, 1.0) ** self.priority_exponent
            for e in experiences
        ]
        total = sum(priorities)
        probs = [p / total for p in priorities]

        # Sample
        indices = np.random.choice(
            len(experiences),
            size=min(batch_size, len(experiences)),
            replace=False,
            p=probs
        )

        sampled = [experiences[i] for i in indices]

        # Update retrieval stats
        for exp in sampled:
            exp.retrieval_count += 1
            exp.last_retrieved = datetime.now()

        return sampled

    def _reservoir_sample(self, batch_size: int) -> List[Experience]:
        """Reservoir sampling for uniform distribution over stream."""
        reservoir = []

        for i, exp in enumerate(self.buffer):
            if i < batch_size:
                reservoir.append(exp)
            else:
                j = random.randint(0, i)
                if j < batch_size:
                    reservoir[j] = exp

        return reservoir

    def update_priority(self, experience_id: str, priority: float) -> None:
        """Update experience priority."""
        self.priorities[experience_id] = priority

    def get_task_experiences(self, task_id: str) -> List[Experience]:
        """Get all experiences for a task."""
        return [e for e in self.buffer if e.task_id == task_id]


class KnowledgeConsolidator:
    """Consolidate knowledge to prevent forgetting."""

    def __init__(self, consolidation_rate: float = 0.1):
        self.consolidation_rate = consolidation_rate
        self.knowledge_graph: Dict[str, KnowledgeNode] = {}

    def add_knowledge(
        self,
        concept: str,
        embedding: List[float] = None,
        importance: float = 1.0
    ) -> str:
        """Add new knowledge node."""
        node_id = str(uuid4())

        self.knowledge_graph[node_id] = KnowledgeNode(
            id=node_id,
            concept=concept,
            embedding=embedding or [],
            importance=importance,
            stability=0.0
        )

        return node_id

    def connect_knowledge(
        self,
        source_id: str,
        target_id: str,
        strength: float = 1.0
    ) -> None:
        """Create connection between knowledge nodes."""
        if source_id in self.knowledge_graph:
            self.knowledge_graph[source_id].connections[target_id] = strength
        if target_id in self.knowledge_graph:
            self.knowledge_graph[target_id].connections[source_id] = strength

    def consolidate(self, node_id: str) -> None:
        """Consolidate knowledge node."""
        if node_id not in self.knowledge_graph:
            return

        node = self.knowledge_graph[node_id]

        # Increase stability
        node.stability = min(1.0, node.stability + self.consolidation_rate)

        # Strengthen connections based on usage
        for connected_id, strength in node.connections.items():
            if connected_id in self.knowledge_graph:
                connected = self.knowledge_graph[connected_id]
                # Hebbian learning - strengthen co-activated connections
                new_strength = min(1.0, strength * (1 + 0.1 * connected.stability))
                node.connections[connected_id] = new_strength

    def get_related_knowledge(
        self,
        concept: str,
        top_k: int = 5
    ) -> List[KnowledgeNode]:
        """Find related knowledge nodes."""
        # Simple text matching for demo (would use embeddings in production)
        concept_words = set(concept.lower().split())

        scores = []
        for node_id, node in self.knowledge_graph.items():
            node_words = set(node.concept.lower().split())
            overlap = len(concept_words & node_words)
            if overlap > 0:
                scores.append((node, overlap * node.importance))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [node for node, _ in scores[:top_k]]


# =============================================================================
# FORGETTING PREVENTION STRATEGIES
# =============================================================================

class ElasticWeightConsolidation:
    """EWC to prevent catastrophic forgetting."""

    def __init__(self, lambda_ewc: float = 1000.0):
        self.lambda_ewc = lambda_ewc
        self.importance_weights: Dict[str, float] = {}
        self.optimal_params: Dict[str, float] = {}
        self.fisher_diagonal: Dict[str, float] = {}

    def compute_fisher_information(
        self,
        param_name: str,
        gradients: List[float]
    ) -> float:
        """Compute Fisher information for parameter."""
        if not gradients:
            return 0.0

        # Fisher information approximated by squared gradients
        fisher = sum(g * g for g in gradients) / len(gradients)
        return fisher

    def register_important_params(
        self,
        params: Dict[str, float],
        task_gradients: Dict[str, List[float]]
    ) -> None:
        """Register important parameters after task learning."""
        for param_name, param_value in params.items():
            # Store optimal parameters
            self.optimal_params[param_name] = param_value

            # Compute Fisher information
            if param_name in task_gradients:
                fisher = self.compute_fisher_information(
                    param_name,
                    task_gradients[param_name]
                )

                # Accumulate Fisher information across tasks
                if param_name in self.fisher_diagonal:
                    self.fisher_diagonal[param_name] += fisher
                else:
                    self.fisher_diagonal[param_name] = fisher

    def compute_penalty(
        self,
        current_params: Dict[str, float]
    ) -> float:
        """Compute EWC penalty for current parameters."""
        penalty = 0.0

        for param_name, current_value in current_params.items():
            if param_name in self.optimal_params:
                diff = current_value - self.optimal_params[param_name]
                fisher = self.fisher_diagonal.get(param_name, 0.0)
                penalty += fisher * diff * diff

        return self.lambda_ewc * penalty / 2


class ProgressiveNetwork:
    """Progressive neural network for lifelong learning."""

    def __init__(self):
        self.columns: List[Dict[str, Any]] = []  # Network columns
        self.lateral_connections: Dict[str, List[str]] = {}
        self.task_to_column: Dict[str, int] = {}

    def add_column(self, task_id: str, architecture: Dict[str, Any]) -> int:
        """Add new column for task."""
        column_idx = len(self.columns)

        self.columns.append({
            "task_id": task_id,
            "architecture": architecture,
            "frozen": False,
            "lateral_from": list(range(column_idx))  # Connect to all previous
        })

        self.task_to_column[task_id] = column_idx

        return column_idx

    def freeze_column(self, column_idx: int) -> None:
        """Freeze column after learning."""
        if column_idx < len(self.columns):
            self.columns[column_idx]["frozen"] = True

    def get_active_columns(self, task_id: str) -> List[int]:
        """Get columns active for task."""
        if task_id in self.task_to_column:
            target_col = self.task_to_column[task_id]
            # Include target column and all lateral connections
            return list(range(target_col + 1))
        return []

    def forward(
        self,
        task_id: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Forward pass through network."""
        active_columns = self.get_active_columns(task_id)

        if not active_columns:
            return {"error": "No column for task"}

        # Simulate forward pass
        outputs = []
        for col_idx in active_columns:
            col = self.columns[col_idx]
            # Each column processes input
            output = {
                "column": col_idx,
                "task": col["task_id"],
                "frozen": col["frozen"]
            }
            outputs.append(output)

        return {
            "task_id": task_id,
            "active_columns": len(active_columns),
            "outputs": outputs
        }


class KnowledgeDistillation:
    """Transfer knowledge from teacher to student."""

    def __init__(self, temperature: float = 2.0):
        self.temperature = temperature
        self.teacher_outputs: Dict[str, List[Dict[str, Any]]] = {}

    def store_teacher_outputs(
        self,
        task_id: str,
        inputs: List[Dict[str, Any]],
        outputs: List[Dict[str, Any]]
    ) -> None:
        """Store teacher outputs for distillation."""
        self.teacher_outputs[task_id] = [
            {"input": inp, "output": out}
            for inp, out in zip(inputs, outputs)
        ]

    def compute_distillation_loss(
        self,
        student_output: Dict[str, float],
        teacher_output: Dict[str, float]
    ) -> float:
        """Compute distillation loss."""
        loss = 0.0

        for key in teacher_output:
            if key in student_output:
                # Soft targets with temperature
                teacher_prob = self._softmax(teacher_output[key])
                student_prob = self._softmax(student_output[key])

                # KL divergence
                if teacher_prob > 0 and student_prob > 0:
                    loss += teacher_prob * math.log(teacher_prob / student_prob)

        return loss * (self.temperature ** 2)

    def _softmax(self, value: float) -> float:
        """Apply softmax with temperature."""
        return math.exp(value / self.temperature)

    def get_distillation_targets(
        self,
        task_id: str
    ) -> List[Dict[str, Any]]:
        """Get distillation targets for task."""
        return self.teacher_outputs.get(task_id, [])


# =============================================================================
# SKILL LEARNING AND TRANSFER
# =============================================================================

class SkillLearner:
    """Learn and manage skills."""

    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self.skill_graph: Dict[str, Set[str]] = defaultdict(set)  # dependencies

    def register_skill(
        self,
        name: str,
        description: str,
        dependencies: List[str] = None
    ) -> str:
        """Register new skill."""
        skill_id = str(uuid4())

        self.skills[skill_id] = Skill(
            id=skill_id,
            name=name,
            description=description,
            dependencies=dependencies or []
        )

        # Update skill graph
        for dep_id in (dependencies or []):
            self.skill_graph[skill_id].add(dep_id)

        return skill_id

    def train_skill(
        self,
        skill_id: str,
        examples: int,
        performance: float
    ) -> None:
        """Train skill with examples."""
        if skill_id not in self.skills:
            return

        skill = self.skills[skill_id]
        skill.training_examples += examples

        # Update proficiency using learning curve
        # Diminishing returns with more examples
        learning_rate = 0.1 / (1 + skill.training_examples / 1000)
        skill.proficiency = min(1.0, skill.proficiency + performance * learning_rate)
        skill.last_practiced = datetime.now()

    def get_skill_proficiency(self, skill_id: str) -> float:
        """Get current skill proficiency."""
        skill = self.skills.get(skill_id)
        if not skill:
            return 0.0

        # Apply decay if not practiced recently
        if skill.last_practiced:
            days_since = (datetime.now() - skill.last_practiced).days
            decay = max(0.5, 1.0 - days_since * 0.01)
            return skill.proficiency * decay

        return skill.proficiency

    def can_learn_skill(self, skill_id: str) -> Tuple[bool, List[str]]:
        """Check if skill can be learned (dependencies met)."""
        skill = self.skills.get(skill_id)
        if not skill:
            return False, []

        missing = []
        for dep_id in skill.dependencies:
            if self.get_skill_proficiency(dep_id) < 0.7:
                dep_skill = self.skills.get(dep_id)
                if dep_skill:
                    missing.append(dep_skill.name)

        return len(missing) == 0, missing


class SkillTransfer:
    """Transfer learning between skills."""

    def __init__(self):
        self.transfer_matrix: Dict[Tuple[str, str], float] = {}
        self.domain_mapping: Dict[str, str] = {}

    def compute_transferability(
        self,
        source_skill_id: str,
        target_skill_id: str,
        source_skill: Skill,
        target_skill: Skill
    ) -> float:
        """Compute transfer potential between skills."""
        # Check cached value
        key = (source_skill_id, target_skill_id)
        if key in self.transfer_matrix:
            return self.transfer_matrix[key]

        # Compute similarity based on:
        # 1. Description overlap
        source_words = set(source_skill.description.lower().split())
        target_words = set(target_skill.description.lower().split())

        if not source_words or not target_words:
            word_overlap = 0.0
        else:
            word_overlap = len(source_words & target_words) / len(source_words | target_words)

        # 2. Shared dependencies
        source_deps = set(source_skill.dependencies)
        target_deps = set(target_skill.dependencies)

        if not source_deps and not target_deps:
            dep_overlap = 0.5  # Neutral
        elif source_deps or target_deps:
            dep_overlap = len(source_deps & target_deps) / len(source_deps | target_deps)
        else:
            dep_overlap = 0.0

        # Combine factors
        transferability = 0.6 * word_overlap + 0.4 * dep_overlap

        # Cache result
        self.transfer_matrix[key] = transferability

        return transferability

    def get_transfer_sources(
        self,
        target_skill_id: str,
        target_skill: Skill,
        available_skills: Dict[str, Skill],
        top_k: int = 3
    ) -> List[Tuple[str, float]]:
        """Find best source skills for transfer."""
        scores = []

        for source_id, source_skill in available_skills.items():
            if source_id == target_skill_id:
                continue

            # Only consider proficient skills
            if source_skill.proficiency < 0.5:
                continue

            score = self.compute_transferability(
                source_id, target_skill_id,
                source_skill, target_skill
            )

            # Weight by source proficiency
            score *= source_skill.proficiency

            scores.append((source_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


# =============================================================================
# CURRICULUM LEARNING
# =============================================================================

class CurriculumScheduler:
    """Schedule tasks for optimal learning."""

    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.task_order: List[str] = []
        self.current_idx: int = 0

    def add_task(self, task: Task) -> None:
        """Add task to curriculum."""
        self.tasks[task.id] = task

    def generate_curriculum(
        self,
        strategy: str = "difficulty"
    ) -> List[str]:
        """Generate ordered curriculum."""
        if strategy == "difficulty":
            # Sort by difficulty (easy to hard)
            sorted_tasks = sorted(
                self.tasks.values(),
                key=lambda t: t.difficulty
            )
        elif strategy == "dependency":
            # Topological sort based on required skills
            sorted_tasks = self._topological_sort()
        elif strategy == "mixed":
            # Mix of difficulties
            sorted_tasks = self._mixed_curriculum()
        else:
            sorted_tasks = list(self.tasks.values())

        self.task_order = [t.id for t in sorted_tasks]
        self.current_idx = 0

        return self.task_order

    def _topological_sort(self) -> List[Task]:
        """Sort tasks by skill dependencies."""
        # Build dependency graph
        skill_tasks: Dict[str, List[str]] = defaultdict(list)
        task_deps: Dict[str, Set[str]] = defaultdict(set)

        for task_id, task in self.tasks.items():
            for skill in task.required_skills:
                skill_tasks[skill].append(task_id)

        # Simple sort by number of dependencies
        return sorted(
            self.tasks.values(),
            key=lambda t: len(t.required_skills)
        )

    def _mixed_curriculum(self) -> List[Task]:
        """Create mixed difficulty curriculum."""
        sorted_by_diff = sorted(
            self.tasks.values(),
            key=lambda t: t.difficulty
        )

        # Interleave: easy, hard, easy, medium, etc.
        n = len(sorted_by_diff)
        if n <= 2:
            return sorted_by_diff

        easy = sorted_by_diff[:n//3]
        medium = sorted_by_diff[n//3:2*n//3]
        hard = sorted_by_diff[2*n//3:]

        result = []
        while easy or medium or hard:
            if easy:
                result.append(easy.pop(0))
            if hard:
                result.append(hard.pop(0))
            if medium:
                result.append(medium.pop(0))

        return result

    def get_next_task(self) -> Optional[Task]:
        """Get next task in curriculum."""
        if self.current_idx >= len(self.task_order):
            return None

        task_id = self.task_order[self.current_idx]
        return self.tasks.get(task_id)

    def advance(self, performance: float) -> bool:
        """Advance to next task if performance is sufficient."""
        if performance >= 0.7:  # Threshold
            self.current_idx += 1
            return True
        return False

    def get_progress(self) -> Dict[str, Any]:
        """Get curriculum progress."""
        return {
            "total_tasks": len(self.task_order),
            "completed": self.current_idx,
            "remaining": len(self.task_order) - self.current_idx,
            "progress_pct": self.current_idx / len(self.task_order) * 100 if self.task_order else 0
        }


# =============================================================================
# CONTINUAL LEARNING SYSTEM
# =============================================================================

class ContinualLearningSystem:
    """Main continual learning orchestrator."""

    def __init__(
        self,
        forgetting_strategy: ForgettingStrategy = ForgettingStrategy.EWC
    ):
        self.forgetting_strategy = forgetting_strategy

        # Components
        self.replay_buffer = ExperienceReplayBuffer()
        self.consolidator = KnowledgeConsolidator()
        self.ewc = ElasticWeightConsolidation()
        self.progressive_net = ProgressiveNetwork()
        self.distillation = KnowledgeDistillation()
        self.skill_learner = SkillLearner()
        self.skill_transfer = SkillTransfer()
        self.curriculum = CurriculumScheduler()

        # State
        self.current_phase = LearningPhase.INITIAL
        self.learned_tasks: List[str] = []
        self.performance_history: Dict[str, List[float]] = defaultdict(list)

    async def learn_task(
        self,
        task: Task,
        training_callback: Callable = None
    ) -> Dict[str, Any]:
        """Learn a new task."""
        logger.info(f"Learning task: {task.name}")

        self.current_phase = LearningPhase.TRAINING

        # 1. Check for transfer opportunities
        transfer_sources = await self._find_transfer_sources(task)

        # 2. Apply forgetting prevention strategy
        if self.forgetting_strategy == ForgettingStrategy.PROGRESSIVE:
            # Add new column to progressive network
            self.progressive_net.add_column(
                task.id,
                {"layers": [128, 64, 32], "activation": "relu"}
            )

        # 3. Train on task
        performance = await self._train_on_task(task, training_callback)

        # 4. Store experiences for replay
        for data in task.training_data:
            exp = Experience(
                id=str(uuid4()),
                task_id=task.id,
                input_data=data.get("input", {}),
                output_data=data.get("output", {}),
                reward=performance
            )
            self.replay_buffer.add(exp)

        # 5. Consolidate knowledge
        self.current_phase = LearningPhase.CONSOLIDATION
        await self._consolidate_task(task, performance)

        # 6. Update skills
        for skill_id in task.required_skills:
            self.skill_learner.train_skill(
                skill_id,
                examples=len(task.training_data),
                performance=performance
            )

        # Record completion
        self.learned_tasks.append(task.id)
        self.performance_history[task.id].append(performance)

        self.current_phase = LearningPhase.INITIAL

        return {
            "task_id": task.id,
            "performance": performance,
            "transfer_used": len(transfer_sources) > 0,
            "experiences_stored": len(task.training_data)
        }

    async def _find_transfer_sources(
        self,
        task: Task
    ) -> List[Tuple[str, float]]:
        """Find skills that can transfer to task."""
        # Create temporary skill for task
        temp_skill = Skill(
            id=task.id,
            name=task.name,
            description=task.description,
            dependencies=task.required_skills
        )

        sources = self.skill_transfer.get_transfer_sources(
            task.id,
            temp_skill,
            self.skill_learner.skills
        )

        if sources:
            logger.info(f"Found {len(sources)} transfer sources for {task.name}")

        return sources

    async def _train_on_task(
        self,
        task: Task,
        callback: Callable = None
    ) -> float:
        """Train on task data."""
        total_performance = 0.0

        for i, data in enumerate(task.training_data):
            # Simulate training step
            step_performance = random.uniform(0.5, 1.0)
            total_performance += step_performance

            if callback:
                await callback(i, len(task.training_data), step_performance)

            # Interleave with replay
            if i % 5 == 0 and len(self.learned_tasks) > 0:
                await self._replay_step()

        avg_performance = total_performance / max(1, len(task.training_data))
        return avg_performance

    async def _replay_step(self) -> None:
        """Perform experience replay step."""
        experiences = self.replay_buffer.sample(8, strategy="prioritized")

        for exp in experiences:
            # Simulate replay training
            # Would actually update model in real implementation
            pass

    async def _consolidate_task(
        self,
        task: Task,
        performance: float
    ) -> None:
        """Consolidate knowledge from task."""
        # Add knowledge to graph
        node_id = self.consolidator.add_knowledge(
            concept=task.name,
            importance=task.difficulty * performance
        )

        # Connect to related knowledge
        for learned_task_id in self.learned_tasks:
            learned_task = self.curriculum.tasks.get(learned_task_id)
            if learned_task:
                # Check for skill overlap
                shared_skills = set(task.required_skills) & set(learned_task.required_skills)
                if shared_skills:
                    self.consolidator.connect_knowledge(
                        node_id,
                        learned_task_id,
                        strength=len(shared_skills) / len(task.required_skills)
                    )

        # Apply EWC if using that strategy
        if self.forgetting_strategy == ForgettingStrategy.EWC:
            # Would register actual model parameters here
            self.ewc.register_important_params(
                params={"weight_1": 0.5, "weight_2": 0.3},
                task_gradients={"weight_1": [0.1, 0.2], "weight_2": [0.05, 0.1]}
            )

        # Freeze progressive network column
        if self.forgetting_strategy == ForgettingStrategy.PROGRESSIVE:
            if task.id in self.progressive_net.task_to_column:
                col_idx = self.progressive_net.task_to_column[task.id]
                self.progressive_net.freeze_column(col_idx)

    async def evaluate_retention(
        self,
        task_ids: List[str] = None
    ) -> Dict[str, float]:
        """Evaluate retention on previous tasks."""
        task_ids = task_ids or self.learned_tasks
        retention = {}

        for task_id in task_ids:
            task = self.curriculum.tasks.get(task_id)
            if not task:
                continue

            # Evaluate on validation data
            if task.validation_data:
                performance = await self._evaluate_task(task)
                retention[task_id] = performance
            else:
                # Use last known performance
                if task_id in self.performance_history:
                    retention[task_id] = self.performance_history[task_id][-1]

        return retention

    async def _evaluate_task(self, task: Task) -> float:
        """Evaluate on task."""
        # Simulate evaluation
        base_performance = random.uniform(0.6, 0.95)

        # Apply forgetting based on strategy effectiveness
        if self.forgetting_strategy == ForgettingStrategy.EWC:
            forgetting_factor = 0.95
        elif self.forgetting_strategy == ForgettingStrategy.PROGRESSIVE:
            forgetting_factor = 0.98
        elif self.forgetting_strategy == ForgettingStrategy.REPLAY:
            forgetting_factor = 0.90
        else:
            forgetting_factor = 0.85

        return base_performance * forgetting_factor

    async def run_curriculum(
        self,
        tasks: List[Task],
        progress_callback: Callable = None
    ) -> Dict[str, Any]:
        """Run through entire curriculum."""
        # Setup curriculum
        for task in tasks:
            self.curriculum.add_task(task)

        self.curriculum.generate_curriculum(strategy="difficulty")

        results = []

        while True:
            task = self.curriculum.get_next_task()
            if not task:
                break

            # Learn task
            result = await self.learn_task(task)
            results.append(result)

            # Advance curriculum
            self.curriculum.advance(result["performance"])

            if progress_callback:
                await progress_callback(self.curriculum.get_progress())

        # Final retention evaluation
        retention = await self.evaluate_retention()

        return {
            "tasks_completed": len(results),
            "results": results,
            "retention": retention,
            "curriculum_progress": self.curriculum.get_progress()
        }

    def get_status(self) -> Dict[str, Any]:
        """Get system status."""
        return {
            "phase": self.current_phase.value,
            "strategy": self.forgetting_strategy.value,
            "learned_tasks": len(self.learned_tasks),
            "experiences_stored": len(self.replay_buffer.buffer),
            "skills": len(self.skill_learner.skills),
            "knowledge_nodes": len(self.consolidator.knowledge_graph)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demo continual learning system."""
    print("=== Continual Learning System Demo ===\n")

    # Create system
    system = ContinualLearningSystem(
        forgetting_strategy=ForgettingStrategy.EWC
    )

    # Register some skills
    skill1 = system.skill_learner.register_skill(
        "basic_math",
        "Basic arithmetic operations"
    )
    skill2 = system.skill_learner.register_skill(
        "algebra",
        "Algebraic manipulation",
        dependencies=[skill1]
    )
    skill3 = system.skill_learner.register_skill(
        "calculus",
        "Differential and integral calculus",
        dependencies=[skill2]
    )

    print("1. Registered Skills:")
    for sid, skill in system.skill_learner.skills.items():
        can_learn, missing = system.skill_learner.can_learn_skill(sid)
        status = "Ready" if can_learn else f"Need: {missing}"
        print(f"   - {skill.name}: {status}")

    # Create tasks
    tasks = [
        Task(
            id="task1",
            name="Addition and Subtraction",
            description="Learn basic addition and subtraction",
            domain="math",
            difficulty=0.2,
            required_skills=[skill1],
            training_data=[{"input": {"a": i, "b": j}, "output": {"sum": i+j}}
                          for i in range(5) for j in range(5)]
        ),
        Task(
            id="task2",
            name="Multiplication",
            description="Learn multiplication operations",
            domain="math",
            difficulty=0.4,
            required_skills=[skill1],
            training_data=[{"input": {"a": i, "b": j}, "output": {"product": i*j}}
                          for i in range(5) for j in range(5)]
        ),
        Task(
            id="task3",
            name="Linear Equations",
            description="Solve linear equations",
            domain="math",
            difficulty=0.6,
            required_skills=[skill2],
            training_data=[{"input": {"equation": f"{i}x + {j} = {i*2+j}"},
                           "output": {"x": 2}} for i in range(1, 6) for j in range(5)]
        ),
        Task(
            id="task4",
            name="Derivatives",
            description="Compute derivatives",
            domain="math",
            difficulty=0.8,
            required_skills=[skill3],
            training_data=[{"input": {"function": f"x^{i}"},
                           "output": {"derivative": f"{i}x^{i-1}"}} for i in range(1, 10)]
        )
    ]

    print("\n2. Running Curriculum:")

    async def progress_cb(progress):
        print(f"   Progress: {progress['completed']}/{progress['total_tasks']} tasks")

    results = await system.run_curriculum(tasks, progress_callback=progress_cb)

    print(f"\n3. Results:")
    for result in results["results"]:
        print(f"   Task {result['task_id']}: Performance = {result['performance']:.2%}")

    print(f"\n4. Retention Evaluation:")
    for task_id, retention in results["retention"].items():
        print(f"   Task {task_id}: Retention = {retention:.2%}")

    print(f"\n5. System Status:")
    status = system.get_status()
    for key, value in status.items():
        print(f"   {key}: {value}")

    # Experience replay demo
    print("\n6. Experience Replay:")
    experiences = system.replay_buffer.sample(3, strategy="prioritized")
    for exp in experiences:
        print(f"   - Task: {exp.task_id}, Reward: {exp.reward:.2f}, Retrieved: {exp.retrieval_count}x")

    # Skill proficiencies
    print("\n7. Skill Proficiencies:")
    for sid, skill in system.skill_learner.skills.items():
        prof = system.skill_learner.get_skill_proficiency(sid)
        print(f"   {skill.name}: {prof:.2%}")


if __name__ == "__main__":
    asyncio.run(demo())
