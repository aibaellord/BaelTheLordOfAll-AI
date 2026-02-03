"""
BAEL Phase 7.4: Advanced Agentic Autonomy
═════════════════════════════════════════════════════════════════════════════

Self-improving autonomous agents with goal hierarchies, reflection mechanisms,
meta-learning, uncertainty quantification, and adaptive strategy selection.

Features:
  • Autonomous Agent Framework
  • Goal Hierarchies & Decomposition
  • Reflection & Self-Monitoring
  • Meta-Learning with Task Adaptation
  • Uncertainty Quantification
  • Strategy Selection & Switching
  • Learning Rate Adaptation
  • Experience Replay & Prioritization
  • Multi-Agent Coordination
  • Agent Introspection
  • Self-Improvement Loops
  • Performance Tracking

Author: BAEL Team
Date: February 2, 2026
"""

import json
import logging
import math
import threading
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Enums & Constants
# ═══════════════════════════════════════════════════════════════════════════

class AgentState(str, Enum):
    """Agent operational state."""
    IDLE = "idle"
    PLANNING = "planning"
    ACTING = "acting"
    REFLECTING = "reflecting"
    LEARNING = "learning"
    ADAPTING = "adapting"
    FAILED = "failed"


class GoalType(str, Enum):
    """Goal types in hierarchy."""
    PRIMARY = "primary"  # Top-level goal
    INTERMEDIATE = "intermediate"  # Sub-goal
    PRIMITIVE = "primitive"  # Directly achievable


class GoalStatus(str, Enum):
    """Goal achievement status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    ACHIEVED = "achieved"
    FAILED = "failed"
    ABANDONED = "abandoned"


class Strategy(str, Enum):
    """Agent strategies."""
    GREEDY = "greedy"  # Exploit best known action
    EXPLORATORY = "exploratory"  # Explore uncertain actions
    BALANCED = "balanced"  # ε-greedy balance
    HIERARCHICAL = "hierarchical"  # Goal-driven
    COLLABORATIVE = "collaborative"  # Multi-agent


class ReflectionType(str, Enum):
    """Types of agent reflection."""
    PERFORMANCE = "performance"  # Evaluate success/failure
    STRATEGY = "strategy"  # Evaluate strategy effectiveness
    LEARNING = "learning"  # Evaluate learning progress
    GOAL = "goal"  # Reassess goal relevance


class UncertaintyType(str, Enum):
    """Types of uncertainty."""
    EPISTEMIC = "epistemic"  # Model uncertainty (reducible)
    ALEATORIC = "aleatoric"  # Data uncertainty (irreducible)
    TECHNICAL = "technical"  # System uncertainty


# ═══════════════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Goal:
    """Goal in agent's objective hierarchy."""
    id: str
    name: str
    description: str
    goal_type: GoalType
    status: GoalStatus = GoalStatus.NOT_STARTED
    parent_id: Optional[str] = None
    subgoals: List[str] = field(default_factory=list)
    success_criteria: Dict[str, float] = field(default_factory=dict)
    deadline: Optional[datetime] = None
    priority: float = 1.0  # [0, 1]
    progress: float = 0.0  # [0, 1]
    attempts: int = 0
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Action:
    """Agent action."""
    id: str
    name: str
    parameters: Dict[str, Any]
    expected_outcome: Optional[Dict[str, float]] = None
    actual_outcome: Optional[Dict[str, float]] = None
    success_probability: float = 0.5
    cost: float = 1.0
    uncertainty: float = 0.0  # [0, 1]


@dataclass
class Experience:
    """Learning experience from action."""
    state: Dict[str, Any]
    action: Action
    reward: float
    next_state: Dict[str, Any]
    done: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetaLearningTask:
    """Meta-learning task for rapid adaptation."""
    task_id: str
    task_type: str
    train_experiences: List[Experience] = field(default_factory=list)
    test_experiences: List[Experience] = field(default_factory=list)
    task_representation: Dict[str, Any] = field(default_factory=dict)
    learning_rate: float = 0.01


@dataclass
class UncertaintyEstimate:
    """Uncertainty quantification."""
    type: UncertaintyType
    mean: float
    std: float
    credible_interval: Tuple[float, float]
    entropy: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AgentPerformanceMetrics:
    """Agent performance tracking."""
    episode_count: int = 0
    total_reward: float = 0.0
    average_reward: float = 0.0
    success_rate: float = 0.0
    goal_achievement_rate: float = 0.0
    learning_curve: List[float] = field(default_factory=list)
    improvement_rate: float = 0.0  # Reward change per episode
    strategy_effectiveness: Dict[str, float] = field(default_factory=dict)
    uncertainty_trend: List[float] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# Goal Hierarchy Manager
# ═══════════════════════════════════════════════════════════════════════════

class GoalHierarchy:
    """Manage hierarchical goal decomposition."""

    def __init__(self):
        """Initialize goal hierarchy."""
        self.goals: Dict[str, Goal] = {}
        self.root_goals: List[str] = []
        self.logger = logging.getLogger(__name__)

    def add_goal(
        self,
        name: str,
        description: str,
        goal_type: GoalType,
        parent_id: Optional[str] = None,
        priority: float = 1.0,
        deadline: Optional[datetime] = None
    ) -> Goal:
        """Add goal to hierarchy."""
        goal_id = str(uuid.uuid4())
        goal = Goal(
            id=goal_id,
            name=name,
            description=description,
            goal_type=goal_type,
            parent_id=parent_id,
            priority=priority,
            deadline=deadline
        )

        self.goals[goal_id] = goal

        if parent_id and parent_id in self.goals:
            self.goals[parent_id].subgoals.append(goal_id)
        else:
            self.root_goals.append(goal_id)

        self.logger.info(f"Added goal: {name} ({goal_id})")
        return goal

    def decompose_goal(self, goal_id: str) -> List[Goal]:
        """Get decomposition of goal into subgoals."""
        if goal_id not in self.goals:
            return []

        goal = self.goals[goal_id]
        subgoals = [self.goals[sid] for sid in goal.subgoals if sid in self.goals]

        return sorted(subgoals, key=lambda g: -g.priority)

    def get_primitive_goals(self, goal_id: str) -> List[Goal]:
        """Get all primitive (leaf) goals under given goal."""
        goal = self.goals.get(goal_id)
        if not goal:
            return []

        if not goal.subgoals:
            return [goal]

        primitives = []
        for subgoal_id in goal.subgoals:
            primitives.extend(self.get_primitive_goals(subgoal_id))

        return primitives

    def update_progress(self, goal_id: str, progress: float) -> None:
        """Update goal progress."""
        if goal_id in self.goals:
            self.goals[goal_id].progress = min(1.0, max(0.0, progress))

            # Update parent progress
            parent_id = self.goals[goal_id].parent_id
            if parent_id and parent_id in self.goals:
                parent = self.goals[parent_id]
                if parent.subgoals:
                    subgoal_progresses = [
                        self.goals[sid].progress
                        for sid in parent.subgoals
                        if sid in self.goals
                    ]
                    parent.progress = sum(subgoal_progresses) / len(subgoal_progresses)

    def mark_goal_achieved(self, goal_id: str) -> None:
        """Mark goal as achieved."""
        if goal_id in self.goals:
            goal = self.goals[goal_id]
            goal.status = GoalStatus.ACHIEVED
            goal.progress = 1.0
            goal.completed_at = datetime.now(timezone.utc)

            self.logger.info(f"Goal achieved: {goal.name}")


# ═══════════════════════════════════════════════════════════════════════════
# Meta-Learning Engine
# ═══════════════════════════════════════════════════════════════════════════

class MetaLearningEngine:
    """Meta-learning for rapid task adaptation."""

    def __init__(self):
        """Initialize meta-learning engine."""
        self.task_embeddings: Dict[str, List[float]] = {}
        self.base_model_params: Dict[str, float] = {}
        self.task_history: List[MetaLearningTask] = []
        self.learning_history: Dict[str, List[float]] = defaultdict(list)
        self.logger = logging.getLogger(__name__)

    def register_task(
        self,
        task_type: str,
        train_experiences: List[Experience],
        test_experiences: Optional[List[Experience]] = None
    ) -> MetaLearningTask:
        """Register meta-learning task."""
        task_id = str(uuid.uuid4())

        task = MetaLearningTask(
            task_id=task_id,
            task_type=task_type,
            train_experiences=train_experiences,
            test_experiences=test_experiences or [],
            task_representation=self._embed_task(task_type, train_experiences)
        )

        self.task_history.append(task)
        self.logger.info(f"Registered meta-learning task: {task_id}")

        return task

    def _embed_task(
        self,
        task_type: str,
        experiences: List[Experience]
    ) -> Dict[str, Any]:
        """Create task embedding."""
        if not experiences:
            return {}

        rewards = [e.reward for e in experiences]
        uncertainties = [e.error or 0.0 for e in experiences]

        return {
            'task_type': task_type,
            'num_experiences': len(experiences),
            'mean_reward': sum(rewards) / len(rewards) if rewards else 0.0,
            'reward_variance': self._variance(rewards),
            'mean_uncertainty': sum(uncertainties) / len(uncertainties) if uncertainties else 0.0,
            'embedding': self._compute_embedding(experiences)
        }

    def adapt_learning_rate(
        self,
        task_id: str,
        base_lr: float,
        performance_history: List[float]
    ) -> float:
        """Adapt learning rate based on task performance."""
        if len(performance_history) < 2:
            return base_lr

        # Compute improvement trend
        recent = performance_history[-5:] if len(performance_history) >= 5 else performance_history
        improvement = recent[-1] - recent[0] if len(recent) > 1 else 0.0

        # Increase LR if improving, decrease if plateauing
        if improvement > 0.1:
            return base_lr * 1.1  # Increase
        elif improvement < 0.01 and len(recent) > 3:
            return base_lr * 0.9  # Decrease

        return base_lr

    def recommend_strategy(self, task_type: str, history: Dict[str, List[float]]) -> Strategy:
        """Recommend strategy based on meta-learning."""
        # Find similar tasks
        similar_tasks = [
            task for task in self.task_history
            if task.task_type == task_type
        ]

        if not similar_tasks:
            return Strategy.BALANCED

        # Analyze strategy effectiveness for similar tasks
        strategy_wins = defaultdict(int)

        for task in similar_tasks:
            if task.test_experiences:
                # Simulate strategy performance
                test_rewards = [e.reward for e in task.test_experiences]
                if test_rewards and sum(test_rewards) > 0:
                    strategy_wins[Strategy.EXPLORATORY] += 1

        if strategy_wins:
            best_strategy = max(strategy_wins.items(), key=lambda x: x[1])[0]
            return best_strategy

        return Strategy.BALANCED

    def _variance(self, values: List[float]) -> float:
        """Compute variance."""
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        return sum((v - mean) ** 2 for v in values) / len(values)

    def _compute_embedding(self, experiences: List[Experience]) -> List[float]:
        """Compute task embedding vector."""
        if not experiences:
            return [0.0] * 8

        rewards = [e.reward for e in experiences]

        embedding = [
            sum(rewards) / len(rewards),  # Mean reward
            self._variance(rewards),  # Reward variance
            min(rewards) if rewards else 0.0,  # Min reward
            max(rewards) if rewards else 0.0,  # Max reward
            len(experiences),  # Task size
            sum(1 for e in experiences if e.done) / len(experiences) if experiences else 0.0,  # Completion rate
            sum(1 for e in experiences if e.error and e.error > 0.1) / len(experiences) if experiences else 0.0,  # Error rate
            len(set(e.action.name for e in experiences)) / max(1, len(experiences))  # Action diversity
        ]

        return embedding


# ═══════════════════════════════════════════════════════════════════════════
# Reflection Engine
# ═══════════════════════════════════════════════════════════════════════════

class ReflectionEngine:
    """Self-reflection and introspection."""

    def __init__(self):
        """Initialize reflection engine."""
        self.reflection_history: List[Dict[str, Any]] = []
        self.insights: List[str] = []
        self.logger = logging.getLogger(__name__)

    def reflect_on_performance(
        self,
        metrics: AgentPerformanceMetrics
    ) -> Dict[str, Any]:
        """Reflect on agent performance."""
        reflection = {
            'type': ReflectionType.PERFORMANCE.value,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metrics': asdict(metrics),
            'insights': [],
            'recommendations': []
        }

        # Performance analysis
        if metrics.improvement_rate > 0.05:
            reflection['insights'].append("Agent is improving steadily")
            reflection['recommendations'].append("Maintain current strategy")
        elif metrics.improvement_rate < -0.02:
            reflection['insights'].append("Agent performance declining")
            reflection['recommendations'].append("Consider strategy change")

        if metrics.success_rate > 0.8:
            reflection['insights'].append("High success rate achieved")
            reflection['recommendations'].append("Increase challenge complexity")
        elif metrics.success_rate < 0.3:
            reflection['insights'].append("Low success rate - learning needed")
            reflection['recommendations'].append("Simplify task or increase exploration")

        self.reflection_history.append(reflection)
        return reflection

    def reflect_on_strategy(
        self,
        current_strategy: Strategy,
        strategy_effectiveness: Dict[str, float]
    ) -> Dict[str, Any]:
        """Reflect on strategy effectiveness."""
        reflection = {
            'type': ReflectionType.STRATEGY.value,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'current_strategy': current_strategy.value,
            'effectiveness_scores': strategy_effectiveness,
            'insights': [],
            'recommended_change': None
        }

        if strategy_effectiveness:
            best_strategy = max(strategy_effectiveness.items(), key=lambda x: x[1])[0]

            if best_strategy != current_strategy.value and strategy_effectiveness[best_strategy] > strategy_effectiveness.get(current_strategy.value, 0) + 0.1:
                reflection['insights'].append(f"{best_strategy} is more effective than {current_strategy.value}")
                reflection['recommended_change'] = best_strategy
            else:
                reflection['insights'].append(f"Current strategy {current_strategy.value} remains effective")

        self.reflection_history.append(reflection)
        return reflection

    def reflect_on_learning(
        self,
        learning_curve: List[float]
    ) -> Dict[str, Any]:
        """Reflect on learning progress."""
        reflection = {
            'type': ReflectionType.LEARNING.value,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'learning_curve_length': len(learning_curve),
            'insights': [],
            'recommendations': []
        }

        if len(learning_curve) > 1:
            recent_improvement = learning_curve[-1] - learning_curve[0]

            if recent_improvement > 0:
                reflection['insights'].append("Learning is progressing positively")
                reflection['recommendations'].append("Continue current learning approach")
            else:
                reflection['insights'].append("Learning progress stalled")
                reflection['recommendations'].append("Try different learning strategy")

        self.reflection_history.append(reflection)
        return reflection


# ═══════════════════════════════════════════════════════════════════════════
# Uncertainty Quantification
# ═══════════════════════════════════════════════════════════════════════════

class UncertaintyQuantifier:
    """Quantify different types of uncertainty."""

    def __init__(self):
        """Initialize uncertainty quantifier."""
        self.uncertainty_estimates: List[UncertaintyEstimate] = []
        self.logger = logging.getLogger(__name__)

    def estimate_epistemic_uncertainty(
        self,
        predictions: List[float],
        num_models: int = 5
    ) -> UncertaintyEstimate:
        """Estimate epistemic (model) uncertainty."""
        # Simulate ensemble predictions
        ensemble_predictions = [predictions for _ in range(num_models)]

        # Compute mean and variance across ensemble
        mean = sum(predictions) / len(predictions) if predictions else 0.0
        variance = sum((p - mean) ** 2 for p in predictions) / len(predictions) if predictions else 0.0
        std = math.sqrt(variance)

        # Credible interval
        ci_lower = mean - 1.96 * std
        ci_upper = mean + 1.96 * std

        # Entropy-based uncertainty
        entropy = self._compute_entropy(predictions)

        estimate = UncertaintyEstimate(
            type=UncertaintyType.EPISTEMIC,
            mean=mean,
            std=std,
            credible_interval=(ci_lower, ci_upper),
            entropy=entropy
        )

        self.uncertainty_estimates.append(estimate)
        return estimate

    def estimate_aleatoric_uncertainty(
        self,
        noise_measurements: List[float]
    ) -> UncertaintyEstimate:
        """Estimate aleatoric (data) uncertainty."""
        mean = sum(noise_measurements) / len(noise_measurements) if noise_measurements else 0.0
        variance = sum((n - mean) ** 2 for n in noise_measurements) / len(noise_measurements) if noise_measurements else 0.0
        std = math.sqrt(variance)

        entropy = self._compute_entropy(noise_measurements)

        estimate = UncertaintyEstimate(
            type=UncertaintyType.ALEATORIC,
            mean=mean,
            std=std,
            credible_interval=(mean - 2 * std, mean + 2 * std),
            entropy=entropy
        )

        self.uncertainty_estimates.append(estimate)
        return estimate

    def estimate_total_uncertainty(
        self,
        epistemic: UncertaintyEstimate,
        aleatoric: UncertaintyEstimate
    ) -> float:
        """Total uncertainty = epistemic + aleatoric."""
        return epistemic.std + aleatoric.std

    def _compute_entropy(self, values: List[float]) -> float:
        """Compute entropy of values (simplified)."""
        if not values:
            return 0.0

        # Normalize to probabilities
        total = sum(abs(v) for v in values)
        if total == 0:
            return 0.0

        probs = [abs(v) / total for v in values]
        entropy = -sum(p * math.log(p + 1e-10) for p in probs)

        return entropy


# ═══════════════════════════════════════════════════════════════════════════
# Autonomous Agent
# ═══════════════════════════════════════════════════════════════════════════

class AutonomousAgent:
    """Self-improving autonomous agent."""

    def __init__(self, agent_id: str):
        """Initialize autonomous agent."""
        self.agent_id = agent_id
        self.state = AgentState.IDLE
        self.goal_hierarchy = GoalHierarchy()
        self.meta_learner = MetaLearningEngine()
        self.reflection_engine = ReflectionEngine()
        self.uncertainty_quantifier = UncertaintyQuantifier()

        self.current_strategy = Strategy.BALANCED
        self.experience_buffer: deque = deque(maxlen=10000)
        self.metrics = AgentPerformanceMetrics()
        self.learning_rate = 0.01

        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()

    def set_primary_goal(
        self,
        name: str,
        description: str,
        deadline: Optional[datetime] = None
    ) -> Goal:
        """Set agent's primary goal."""
        with self._lock:
            goal = self.goal_hierarchy.add_goal(
                name=name,
                description=description,
                goal_type=GoalType.PRIMARY,
                deadline=deadline,
                priority=1.0
            )
            self.logger.info(f"Primary goal set: {name}")
            return goal

    def decompose_goal(self, goal_id: str) -> List[Goal]:
        """Decompose goal into subgoals."""
        with self._lock:
            return self.goal_hierarchy.decompose_goal(goal_id)

    def act(
        self,
        current_state: Dict[str, Any],
        available_actions: List[Action]
    ) -> Action:
        """Select and execute action based on strategy."""
        with self._lock:
            self.state = AgentState.ACTING

            if self.current_strategy == Strategy.GREEDY:
                action = self._select_greedy(available_actions)
            elif self.current_strategy == Strategy.EXPLORATORY:
                action = self._select_exploratory(available_actions)
            elif self.current_strategy == Strategy.HIERARCHICAL:
                action = self._select_hierarchical(available_actions, current_state)
            else:  # BALANCED
                action = self._select_balanced(available_actions)

            self.state = AgentState.IDLE
            return action

    def _select_greedy(self, actions: List[Action]) -> Action:
        """Greedy action selection."""
        if not actions:
            return Action(id=str(uuid.uuid4()), name="noop", parameters={})

        return max(actions, key=lambda a: a.success_probability)

    def _select_exploratory(self, actions: List[Action]) -> Action:
        """Exploratory action selection."""
        if not actions:
            return Action(id=str(uuid.uuid4()), name="noop", parameters={})

        # Select action with highest uncertainty
        return max(actions, key=lambda a: a.uncertainty)

    def _select_balanced(self, actions: List[Action]) -> Action:
        """ε-greedy balanced selection."""
        if not actions:
            return Action(id=str(uuid.uuid4()), name="noop", parameters={})

        epsilon = 0.1
        rand_val = (sum(a.cost for a in actions) * 0.3) % 1.0

        if rand_val < epsilon:
            # Explore
            return max(actions, key=lambda a: a.uncertainty)
        else:
            # Exploit
            return max(actions, key=lambda a: a.success_probability)

    def _select_hierarchical(
        self,
        actions: List[Action],
        current_state: Dict[str, Any]
    ) -> Action:
        """Hierarchical goal-driven action selection."""
        # Select action aligned with active goals
        if not actions:
            return Action(id=str(uuid.uuid4()), name="noop", parameters={})

        goal_aligned_actions = [
            a for a in actions
            if any(sg in a.name for sg in self._get_active_subgoal_names())
        ]

        if goal_aligned_actions:
            return max(goal_aligned_actions, key=lambda a: a.success_probability)

        return self._select_greedy(actions)

    def _get_active_subgoal_names(self) -> List[str]:
        """Get names of active subgoals."""
        names = []
        for root_id in self.goal_hierarchy.root_goals:
            primitives = self.goal_hierarchy.get_primitive_goals(root_id)
            for g in primitives:
                if g.status == GoalStatus.IN_PROGRESS:
                    names.append(g.name.lower())
        return names

    def learn_from_experience(
        self,
        state: Dict[str, Any],
        action: Action,
        reward: float,
        next_state: Dict[str, Any],
        done: bool
    ) -> None:
        """Learn from experience."""
        with self._lock:
            self.state = AgentState.LEARNING

            experience = Experience(
                state=state,
                action=action,
                reward=reward,
                next_state=next_state,
                done=done
            )

            self.experience_buffer.append(experience)
            self.metrics.episode_count += 1
            self.metrics.total_reward += reward
            self.metrics.average_reward = self.metrics.total_reward / self.metrics.episode_count
            self.metrics.learning_curve.append(self.metrics.average_reward)

            # Compute improvement rate
            if len(self.metrics.learning_curve) > 1:
                self.metrics.improvement_rate = (
                    self.metrics.learning_curve[-1] - self.metrics.learning_curve[-2]
                )

            self.state = AgentState.IDLE

    def reflect(self) -> Dict[str, Any]:
        """Perform self-reflection and introspection."""
        with self._lock:
            self.state = AgentState.REFLECTING

            # Reflect on performance
            perf_reflection = self.reflection_engine.reflect_on_performance(self.metrics)

            # Reflect on strategy
            strat_effectiveness = {
                'greedy': 0.6,
                'exploratory': 0.7,
                'balanced': 0.8,
                'hierarchical': 0.75
            }
            strat_reflection = self.reflection_engine.reflect_on_strategy(
                self.current_strategy,
                strat_effectiveness
            )

            # Reflect on learning
            learn_reflection = self.reflection_engine.reflect_on_learning(
                self.metrics.learning_curve
            )

            # Execute recommendations
            if strat_reflection.get('recommended_change'):
                new_strategy = strat_reflection['recommended_change']
                try:
                    self.current_strategy = Strategy[new_strategy.upper()]
                    self.logger.info(f"Strategy changed to {new_strategy}")
                except KeyError:
                    pass

            self.state = AgentState.IDLE

            return {
                'performance': perf_reflection,
                'strategy': strat_reflection,
                'learning': learn_reflection
            }

    def adapt(self, task_type: str) -> None:
        """Adapt to new task using meta-learning."""
        with self._lock:
            self.state = AgentState.ADAPTING

            # Get experiences for meta-learning
            experiences = list(self.experience_buffer)

            if experiences:
                # Register task
                task = self.meta_learner.register_task(task_type, experiences)

                # Adapt learning rate
                if self.metrics.learning_curve:
                    self.learning_rate = self.meta_learner.adapt_learning_rate(
                        task.task_id,
                        self.learning_rate,
                        self.metrics.learning_curve
                    )

                # Recommend strategy
                recommended = self.meta_learner.recommend_strategy(
                    task_type,
                    {}
                )
                if recommended != self.current_strategy:
                    self.current_strategy = recommended
                    self.logger.info(f"Adapted strategy to {recommended.value}")

            self.state = AgentState.IDLE

    def quantify_uncertainty(self) -> Dict[str, Any]:
        """Quantify current uncertainty."""
        with self._lock:
            if not self.metrics.learning_curve or len(self.metrics.learning_curve) < 2:
                return {}

            recent_rewards = list(self.metrics.learning_curve)[-20:]

            epistemic = self.uncertainty_quantifier.estimate_epistemic_uncertainty(recent_rewards)
            aleatoric = self.uncertainty_quantifier.estimate_aleatoric_uncertainty(recent_rewards)
            total_unc = self.uncertainty_quantifier.estimate_total_uncertainty(epistemic, aleatoric)

            self.metrics.uncertainty_trend.append(total_unc)

            return {
                'epistemic': asdict(epistemic),
                'aleatoric': asdict(aleatoric),
                'total': total_unc
            }

    def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        with self._lock:
            return {
                'agent_id': self.agent_id,
                'state': self.state.value,
                'strategy': self.current_strategy.value,
                'learning_rate': self.learning_rate,
                'metrics': asdict(self.metrics),
                'num_experiences': len(self.experience_buffer)
            }


# ═══════════════════════════════════════════════════════════════════════════
# Multi-Agent Coordination
# ═══════════════════════════════════════════════════════════════════════════

class MultiAgentCoordinator:
    """Coordinate multiple autonomous agents."""

    def __init__(self):
        """Initialize multi-agent coordinator."""
        self.agents: Dict[str, AutonomousAgent] = {}
        self.shared_knowledge: Dict[str, Any] = {}
        self.collaboration_metrics: Dict[str, float] = {}
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()

    def register_agent(self, agent: AutonomousAgent) -> None:
        """Register agent."""
        with self._lock:
            self.agents[agent.agent_id] = agent
            self.logger.info(f"Registered agent: {agent.agent_id}")

    def share_experience(
        self,
        agent_id: str,
        experience: Experience
    ) -> None:
        """Share learning experience across agents."""
        with self._lock:
            # Store in shared knowledge
            key = f"{agent_id}_{experience.action.name}"
            self.shared_knowledge[key] = experience

            # Propagate to other agents
            source_agent = self.agents.get(agent_id)
            if source_agent:
                for other_id, other_agent in self.agents.items():
                    if other_id != agent_id:
                        # Other agent can learn from experience
                        other_agent.learn_from_experience(
                            experience.state,
                            experience.action,
                            experience.reward * 0.9,  # Discount cross-agent learning
                            experience.next_state,
                            experience.done
                        )

    def coordinate_on_shared_goal(
        self,
        goal: Goal
    ) -> List[Action]:
        """Coordinate multiple agents on shared goal."""
        with self._lock:
            coordinated_actions = []

            for agent in self.agents.values():
                agent.goal_hierarchy.goals[goal.id] = goal

            return coordinated_actions


# ═══════════════════════════════════════════════════════════════════════════
# Global Agent Manager Singleton
# ═══════════════════════════════════════════════════════════════════════════

_global_multi_agent_coordinator: Optional[MultiAgentCoordinator] = None


def get_multi_agent_coordinator() -> MultiAgentCoordinator:
    """Get or create global multi-agent coordinator."""
    global _global_multi_agent_coordinator
    if _global_multi_agent_coordinator is None:
        _global_multi_agent_coordinator = MultiAgentCoordinator()
    return _global_multi_agent_coordinator


def create_autonomous_agent(agent_id: str) -> AutonomousAgent:
    """Create and register new autonomous agent."""
    agent = AutonomousAgent(agent_id)
    coordinator = get_multi_agent_coordinator()
    coordinator.register_agent(agent)
    return agent
