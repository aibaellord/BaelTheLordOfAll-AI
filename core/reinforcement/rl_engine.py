"""
BAEL - Reinforcement Learning Engine
Advanced RL for adaptive decision-making and strategy optimization.

Features:
- Multi-Armed Bandits (Explore vs Exploit)
- Q-Learning for action selection
- Policy Gradients for complex decisions
- Actor-Critic for balanced learning
- Contextual Bandits for personalization
- Reward shaping and credit assignment
"""

import asyncio
import hashlib
import json
import logging
import random
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("BAEL.Reinforcement")


# =============================================================================
# ENUMS
# =============================================================================

class RLAlgorithm(Enum):
    """RL algorithm types."""
    EPSILON_GREEDY = "epsilon_greedy"
    UCB = "ucb"
    THOMPSON_SAMPLING = "thompson_sampling"
    Q_LEARNING = "q_learning"
    SARSA = "sarsa"
    DQN = "dqn"
    POLICY_GRADIENT = "policy_gradient"
    ACTOR_CRITIC = "actor_critic"
    PPO = "ppo"
    CONTEXTUAL_BANDIT = "contextual_bandit"


class RewardType(Enum):
    """Types of rewards."""
    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    SHAPED = "shaped"
    SPARSE = "sparse"
    DENSE = "dense"
    INTRINSIC = "intrinsic"


class ExplorationStrategy(Enum):
    """Exploration strategies."""
    EPSILON_GREEDY = "epsilon_greedy"
    BOLTZMANN = "boltzmann"
    UCB = "ucb"
    THOMPSON = "thompson"
    CURIOSITY = "curiosity"
    COUNT_BASED = "count_based"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class State:
    """Represents an RL state."""
    id: str
    features: Dict[str, Any]
    vector: Optional[np.ndarray] = None
    timestamp: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_context(cls, context: Dict[str, Any]) -> "State":
        """Create state from context."""
        state_id = hashlib.md5(json.dumps(context, sort_keys=True, default=str).encode()).hexdigest()[:12]
        return cls(id=state_id, features=context)

    def to_vector(self, feature_dim: int = 64) -> np.ndarray:
        """Convert to vector representation."""
        if self.vector is not None:
            return self.vector
        # Simple hashing for demo
        hash_val = int(self.id, 16)
        np.random.seed(hash_val % 2**32)
        self.vector = np.random.randn(feature_dim)
        return self.vector


@dataclass
class Action:
    """Represents an action."""
    id: str
    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    cost: float = 0.0

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id if isinstance(other, Action) else False


@dataclass
class Experience:
    """Experience tuple for replay."""
    state: State
    action: Action
    reward: float
    next_state: Optional[State]
    done: bool
    info: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Policy:
    """RL Policy."""
    name: str
    algorithm: RLAlgorithm
    parameters: Dict[str, Any] = field(default_factory=dict)
    performance: float = 0.0


# =============================================================================
# REWARD FUNCTIONS
# =============================================================================

class RewardFunction(ABC):
    """Base reward function."""

    @abstractmethod
    def compute(self, state: State, action: Action, next_state: State, info: Dict) -> float:
        pass


class TaskSuccessReward(RewardFunction):
    """Reward based on task completion."""

    def __init__(self, success_reward: float = 1.0, failure_penalty: float = -0.5):
        self.success_reward = success_reward
        self.failure_penalty = failure_penalty

    def compute(self, state: State, action: Action, next_state: State, info: Dict) -> float:
        if info.get("success"):
            return self.success_reward
        elif info.get("failure"):
            return self.failure_penalty
        return 0.0


class EfficiencyReward(RewardFunction):
    """Reward based on efficiency metrics."""

    def __init__(self, time_weight: float = 0.3, cost_weight: float = 0.3, quality_weight: float = 0.4):
        self.time_weight = time_weight
        self.cost_weight = cost_weight
        self.quality_weight = quality_weight

    def compute(self, state: State, action: Action, next_state: State, info: Dict) -> float:
        time_factor = 1.0 - min(info.get("time_taken", 1.0) / 10.0, 1.0)
        cost_factor = 1.0 - min(action.cost / 1.0, 1.0)
        quality_factor = info.get("quality", 0.5)

        return (self.time_weight * time_factor +
                self.cost_weight * cost_factor +
                self.quality_weight * quality_factor)


class CuriosityReward(RewardFunction):
    """Intrinsic curiosity-driven reward."""

    def __init__(self, novelty_weight: float = 0.5):
        self.novelty_weight = novelty_weight
        self.seen_states: set = set()

    def compute(self, state: State, action: Action, next_state: State, info: Dict) -> float:
        novelty = 1.0 if next_state.id not in self.seen_states else 0.0
        self.seen_states.add(next_state.id)
        return self.novelty_weight * novelty


class CompositeReward(RewardFunction):
    """Combines multiple reward functions."""

    def __init__(self, reward_functions: List[Tuple[RewardFunction, float]]):
        self.reward_functions = reward_functions

    def compute(self, state: State, action: Action, next_state: State, info: Dict) -> float:
        total = 0.0
        for reward_fn, weight in self.reward_functions:
            total += weight * reward_fn.compute(state, action, next_state, info)
        return total


# =============================================================================
# MULTI-ARMED BANDIT
# =============================================================================

class MultiArmedBandit:
    """Multi-armed bandit for action selection."""

    def __init__(self, n_arms: int, strategy: ExplorationStrategy = ExplorationStrategy.UCB):
        self.n_arms = n_arms
        self.strategy = strategy
        self.counts = np.zeros(n_arms)
        self.values = np.zeros(n_arms)
        self.total_count = 0

        # Thompson sampling priors
        self.alpha = np.ones(n_arms)
        self.beta = np.ones(n_arms)

    def select_arm(self, epsilon: float = 0.1, temperature: float = 1.0) -> int:
        """Select arm based on strategy."""
        if self.strategy == ExplorationStrategy.EPSILON_GREEDY:
            if random.random() < epsilon:
                return random.randint(0, self.n_arms - 1)
            return int(np.argmax(self.values))

        elif self.strategy == ExplorationStrategy.BOLTZMANN:
            exp_values = np.exp(self.values / temperature)
            probs = exp_values / np.sum(exp_values)
            return int(np.random.choice(self.n_arms, p=probs))

        elif self.strategy == ExplorationStrategy.UCB:
            if self.total_count < self.n_arms:
                return self.total_count
            ucb_values = self.values + np.sqrt(2 * np.log(self.total_count) / (self.counts + 1e-8))
            return int(np.argmax(ucb_values))

        elif self.strategy == ExplorationStrategy.THOMPSON:
            samples = np.random.beta(self.alpha, self.beta)
            return int(np.argmax(samples))

        return random.randint(0, self.n_arms - 1)

    def update(self, arm: int, reward: float) -> None:
        """Update arm values."""
        self.counts[arm] += 1
        self.total_count += 1

        # Running average update
        n = self.counts[arm]
        self.values[arm] = ((n - 1) / n) * self.values[arm] + (1 / n) * reward

        # Thompson sampling update
        if reward > 0:
            self.alpha[arm] += 1
        else:
            self.beta[arm] += 1


# =============================================================================
# Q-LEARNING
# =============================================================================

class QLearningAgent:
    """Q-Learning agent for discrete state-action spaces."""

    def __init__(
        self,
        actions: List[Action],
        learning_rate: float = 0.1,
        discount_factor: float = 0.99,
        epsilon: float = 0.1,
        epsilon_decay: float = 0.995,
        min_epsilon: float = 0.01
    ):
        self.actions = actions
        self.action_map = {a.id: i for i, a in enumerate(actions)}
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon

        self.q_table: Dict[str, np.ndarray] = {}

    def get_q_values(self, state: State) -> np.ndarray:
        """Get Q-values for state."""
        if state.id not in self.q_table:
            self.q_table[state.id] = np.zeros(len(self.actions))
        return self.q_table[state.id]

    def select_action(self, state: State) -> Action:
        """Select action using epsilon-greedy."""
        if random.random() < self.epsilon:
            return random.choice(self.actions)

        q_values = self.get_q_values(state)
        return self.actions[int(np.argmax(q_values))]

    def update(self, state: State, action: Action, reward: float,
               next_state: Optional[State], done: bool) -> float:
        """Update Q-values."""
        q_values = self.get_q_values(state)
        action_idx = self.action_map[action.id]

        if done or next_state is None:
            target = reward
        else:
            next_q_values = self.get_q_values(next_state)
            target = reward + self.discount_factor * np.max(next_q_values)

        td_error = target - q_values[action_idx]
        q_values[action_idx] += self.learning_rate * td_error

        # Decay epsilon
        self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)

        return td_error


# =============================================================================
# POLICY GRADIENT
# =============================================================================

class PolicyGradientAgent:
    """Policy gradient agent for continuous action selection."""

    def __init__(
        self,
        state_dim: int,
        n_actions: int,
        hidden_dim: int = 64,
        learning_rate: float = 0.01
    ):
        self.state_dim = state_dim
        self.n_actions = n_actions
        self.learning_rate = learning_rate

        # Simple linear policy network (weights)
        self.W1 = np.random.randn(state_dim, hidden_dim) * 0.1
        self.b1 = np.zeros(hidden_dim)
        self.W2 = np.random.randn(hidden_dim, n_actions) * 0.1
        self.b2 = np.zeros(n_actions)

        # Episode storage
        self.states: List[np.ndarray] = []
        self.actions: List[int] = []
        self.rewards: List[float] = []

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        """Softmax function."""
        exp_x = np.exp(x - np.max(x))
        return exp_x / np.sum(exp_x)

    def _forward(self, state: np.ndarray) -> np.ndarray:
        """Forward pass."""
        hidden = np.tanh(np.dot(state, self.W1) + self.b1)
        logits = np.dot(hidden, self.W2) + self.b2
        return self._softmax(logits)

    def select_action(self, state: State) -> int:
        """Select action from policy."""
        state_vec = state.to_vector(self.state_dim)
        probs = self._forward(state_vec)
        action = np.random.choice(self.n_actions, p=probs)

        self.states.append(state_vec)
        self.actions.append(action)

        return action

    def store_reward(self, reward: float) -> None:
        """Store reward for current step."""
        self.rewards.append(reward)

    def update(self, gamma: float = 0.99) -> float:
        """Update policy using REINFORCE."""
        if not self.rewards:
            return 0.0

        # Compute returns
        returns = []
        G = 0
        for r in reversed(self.rewards):
            G = r + gamma * G
            returns.insert(0, G)
        returns = np.array(returns)

        # Normalize
        if len(returns) > 1:
            returns = (returns - np.mean(returns)) / (np.std(returns) + 1e-8)

        # Compute gradients and update
        total_loss = 0.0
        for state, action, G in zip(self.states, self.actions, returns):
            probs = self._forward(state)

            # Gradient of log probability
            grad_log = np.zeros(self.n_actions)
            grad_log[action] = 1.0 - probs[action]

            # Simple gradient update (approximate)
            hidden = np.tanh(np.dot(state, self.W1) + self.b1)
            self.W2 += self.learning_rate * G * np.outer(hidden, grad_log)
            self.b2 += self.learning_rate * G * grad_log

            total_loss += -np.log(probs[action]) * G

        # Clear episode
        self.states.clear()
        self.actions.clear()
        self.rewards.clear()

        return total_loss


# =============================================================================
# ACTOR-CRITIC
# =============================================================================

class ActorCriticAgent:
    """Actor-Critic agent."""

    def __init__(
        self,
        state_dim: int,
        n_actions: int,
        hidden_dim: int = 64,
        actor_lr: float = 0.01,
        critic_lr: float = 0.05
    ):
        self.state_dim = state_dim
        self.n_actions = n_actions
        self.actor_lr = actor_lr
        self.critic_lr = critic_lr

        # Actor network (policy)
        self.actor_W1 = np.random.randn(state_dim, hidden_dim) * 0.1
        self.actor_b1 = np.zeros(hidden_dim)
        self.actor_W2 = np.random.randn(hidden_dim, n_actions) * 0.1
        self.actor_b2 = np.zeros(n_actions)

        # Critic network (value function)
        self.critic_W1 = np.random.randn(state_dim, hidden_dim) * 0.1
        self.critic_b1 = np.zeros(hidden_dim)
        self.critic_W2 = np.random.randn(hidden_dim, 1) * 0.1
        self.critic_b2 = np.zeros(1)

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        exp_x = np.exp(x - np.max(x))
        return exp_x / np.sum(exp_x)

    def _policy(self, state: np.ndarray) -> np.ndarray:
        """Get action probabilities."""
        hidden = np.tanh(np.dot(state, self.actor_W1) + self.actor_b1)
        logits = np.dot(hidden, self.actor_W2) + self.actor_b2
        return self._softmax(logits)

    def _value(self, state: np.ndarray) -> float:
        """Get state value."""
        hidden = np.tanh(np.dot(state, self.critic_W1) + self.critic_b1)
        value = np.dot(hidden, self.critic_W2) + self.critic_b2
        return float(value[0])

    def select_action(self, state: State) -> int:
        """Select action from policy."""
        state_vec = state.to_vector(self.state_dim)
        probs = self._policy(state_vec)
        return int(np.random.choice(self.n_actions, p=probs))

    def update(
        self,
        state: State,
        action: int,
        reward: float,
        next_state: Optional[State],
        done: bool,
        gamma: float = 0.99
    ) -> Tuple[float, float]:
        """Update actor and critic."""
        state_vec = state.to_vector(self.state_dim)

        # Get current value
        current_value = self._value(state_vec)

        # Get next value
        if done or next_state is None:
            next_value = 0.0
        else:
            next_state_vec = next_state.to_vector(self.state_dim)
            next_value = self._value(next_state_vec)

        # TD error (advantage)
        td_target = reward + gamma * next_value
        advantage = td_target - current_value

        # Update critic
        critic_hidden = np.tanh(np.dot(state_vec, self.critic_W1) + self.critic_b1)
        self.critic_W2 += self.critic_lr * advantage * critic_hidden.reshape(-1, 1)
        self.critic_b2 += self.critic_lr * advantage

        # Update actor
        probs = self._policy(state_vec)
        grad_log = np.zeros(self.n_actions)
        grad_log[action] = 1.0 - probs[action]

        actor_hidden = np.tanh(np.dot(state_vec, self.actor_W1) + self.actor_b1)
        self.actor_W2 += self.actor_lr * advantage * np.outer(actor_hidden, grad_log)
        self.actor_b2 += self.actor_lr * advantage * grad_log

        return advantage, td_target - current_value


# =============================================================================
# EXPERIENCE REPLAY
# =============================================================================

class ExperienceReplayBuffer:
    """Experience replay buffer for off-policy learning."""

    def __init__(self, capacity: int = 10000, prioritized: bool = False):
        self.capacity = capacity
        self.prioritized = prioritized
        self.buffer: List[Experience] = []
        self.priorities: np.ndarray = np.array([])
        self.position = 0

    def add(self, experience: Experience, priority: float = 1.0) -> None:
        """Add experience to buffer."""
        if len(self.buffer) < self.capacity:
            self.buffer.append(experience)
            self.priorities = np.append(self.priorities, priority)
        else:
            self.buffer[self.position] = experience
            self.priorities[self.position] = priority

        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size: int) -> List[Experience]:
        """Sample batch of experiences."""
        if self.prioritized and len(self.priorities) > 0:
            probs = self.priorities / np.sum(self.priorities)
            indices = np.random.choice(len(self.buffer), size=min(batch_size, len(self.buffer)),
                                       p=probs, replace=False)
        else:
            indices = np.random.choice(len(self.buffer), size=min(batch_size, len(self.buffer)),
                                       replace=False)

        return [self.buffer[i] for i in indices]

    def update_priority(self, index: int, priority: float) -> None:
        """Update priority for prioritized replay."""
        if index < len(self.priorities):
            self.priorities[index] = priority

    def __len__(self) -> int:
        return len(self.buffer)


# =============================================================================
# CONTEXTUAL BANDIT
# =============================================================================

class ContextualBandit:
    """Contextual bandit for personalized action selection."""

    def __init__(
        self,
        context_dim: int,
        n_actions: int,
        learning_rate: float = 0.01
    ):
        self.context_dim = context_dim
        self.n_actions = n_actions
        self.learning_rate = learning_rate

        # Linear model for each arm
        self.weights = np.zeros((n_actions, context_dim))
        self.counts = np.zeros(n_actions)

    def predict_rewards(self, context: np.ndarray) -> np.ndarray:
        """Predict reward for each action given context."""
        return np.dot(self.weights, context)

    def select_action(self, context: np.ndarray, epsilon: float = 0.1) -> int:
        """Select action given context."""
        if random.random() < epsilon:
            return random.randint(0, self.n_actions - 1)

        predicted_rewards = self.predict_rewards(context)
        return int(np.argmax(predicted_rewards))

    def update(self, context: np.ndarray, action: int, reward: float) -> None:
        """Update model for chosen action."""
        predicted = np.dot(self.weights[action], context)
        error = reward - predicted
        self.weights[action] += self.learning_rate * error * context
        self.counts[action] += 1


# =============================================================================
# RL ENGINE
# =============================================================================

class ReinforcementLearningEngine:
    """
    Main Reinforcement Learning Engine for BAEL.

    Provides a unified interface for various RL algorithms
    to optimize BAEL's decision-making processes.
    """

    def __init__(
        self,
        actions: List[Action],
        state_dim: int = 64,
        algorithm: RLAlgorithm = RLAlgorithm.Q_LEARNING,
        reward_function: Optional[RewardFunction] = None
    ):
        self.actions = actions
        self.state_dim = state_dim
        self.algorithm = algorithm
        self.reward_function = reward_function or TaskSuccessReward()

        # Initialize agents
        self.q_agent = QLearningAgent(actions)
        self.policy_agent = PolicyGradientAgent(state_dim, len(actions))
        self.actor_critic = ActorCriticAgent(state_dim, len(actions))
        self.contextual_bandit = ContextualBandit(state_dim, len(actions))

        # Bandits for action selection
        self.bandit = MultiArmedBandit(len(actions))

        # Experience replay
        self.replay_buffer = ExperienceReplayBuffer(capacity=10000, prioritized=True)

        # Statistics
        self.episode_rewards: List[float] = []
        self.episode_lengths: List[int] = []
        self.total_steps = 0

        logger.info(f"RL Engine initialized with algorithm: {algorithm.value}")

    async def select_action(
        self,
        state: State,
        context: Optional[Dict[str, Any]] = None
    ) -> Action:
        """
        Select action based on current state.

        Args:
            state: Current state
            context: Optional additional context

        Returns:
            Selected action
        """
        if self.algorithm == RLAlgorithm.Q_LEARNING:
            return self.q_agent.select_action(state)

        elif self.algorithm == RLAlgorithm.POLICY_GRADIENT:
            action_idx = self.policy_agent.select_action(state)
            return self.actions[action_idx]

        elif self.algorithm == RLAlgorithm.ACTOR_CRITIC:
            action_idx = self.actor_critic.select_action(state)
            return self.actions[action_idx]

        elif self.algorithm == RLAlgorithm.CONTEXTUAL_BANDIT:
            context_vec = state.to_vector(self.state_dim)
            action_idx = self.contextual_bandit.select_action(context_vec)
            return self.actions[action_idx]

        elif self.algorithm in [RLAlgorithm.EPSILON_GREEDY, RLAlgorithm.UCB,
                                  RLAlgorithm.THOMPSON_SAMPLING]:
            arm = self.bandit.select_arm()
            return self.actions[arm]

        # Default: random
        return random.choice(self.actions)

    async def step(
        self,
        state: State,
        action: Action,
        next_state: Optional[State],
        info: Dict[str, Any],
        done: bool = False
    ) -> Experience:
        """
        Process a step and update the agent.

        Args:
            state: Current state
            action: Action taken
            next_state: Resulting state
            info: Additional information
            done: Whether episode is done

        Returns:
            Experience tuple
        """
        # Compute reward
        reward = self.reward_function.compute(state, action, next_state or state, info)

        # Create experience
        experience = Experience(
            state=state,
            action=action,
            reward=reward,
            next_state=next_state,
            done=done,
            info=info
        )

        # Add to replay buffer
        self.replay_buffer.add(experience)

        # Update agent
        if self.algorithm == RLAlgorithm.Q_LEARNING:
            self.q_agent.update(state, action, reward, next_state, done)

        elif self.algorithm == RLAlgorithm.POLICY_GRADIENT:
            self.policy_agent.store_reward(reward)
            if done:
                self.policy_agent.update()

        elif self.algorithm == RLAlgorithm.ACTOR_CRITIC:
            action_idx = self.actions.index(action)
            self.actor_critic.update(state, action_idx, reward, next_state, done)

        elif self.algorithm == RLAlgorithm.CONTEXTUAL_BANDIT:
            context_vec = state.to_vector(self.state_dim)
            action_idx = self.actions.index(action)
            self.contextual_bandit.update(context_vec, action_idx, reward)

        elif self.algorithm in [RLAlgorithm.EPSILON_GREEDY, RLAlgorithm.UCB,
                                  RLAlgorithm.THOMPSON_SAMPLING]:
            arm = self.actions.index(action)
            self.bandit.update(arm, reward)

        self.total_steps += 1

        return experience

    async def learn_from_replay(self, batch_size: int = 32) -> float:
        """
        Learn from experience replay buffer.

        Args:
            batch_size: Number of experiences to sample

        Returns:
            Average loss
        """
        if len(self.replay_buffer) < batch_size:
            return 0.0

        experiences = self.replay_buffer.sample(batch_size)
        total_loss = 0.0

        for exp in experiences:
            if self.algorithm == RLAlgorithm.Q_LEARNING:
                td_error = self.q_agent.update(
                    exp.state, exp.action, exp.reward, exp.next_state, exp.done
                )
                total_loss += abs(td_error)

        return total_loss / len(experiences)

    def get_policy_summary(self) -> Dict[str, Any]:
        """Get summary of current policy."""
        summary = {
            "algorithm": self.algorithm.value,
            "total_steps": self.total_steps,
            "replay_buffer_size": len(self.replay_buffer),
            "actions": [a.name for a in self.actions]
        }

        if self.algorithm == RLAlgorithm.Q_LEARNING:
            summary["epsilon"] = self.q_agent.epsilon
            summary["states_visited"] = len(self.q_agent.q_table)

        elif self.algorithm in [RLAlgorithm.EPSILON_GREEDY, RLAlgorithm.UCB,
                                  RLAlgorithm.THOMPSON_SAMPLING]:
            summary["arm_values"] = self.bandit.values.tolist()
            summary["arm_counts"] = self.bandit.counts.tolist()

        return summary

    def save_policy(self, path: str) -> None:
        """Save policy to file."""
        policy_data = {
            "algorithm": self.algorithm.value,
            "total_steps": self.total_steps
        }

        if self.algorithm == RLAlgorithm.Q_LEARNING:
            policy_data["q_table"] = {k: v.tolist() for k, v in self.q_agent.q_table.items()}
            policy_data["epsilon"] = self.q_agent.epsilon

        with open(path, 'w') as f:
            json.dump(policy_data, f, indent=2)

        logger.info(f"Policy saved to {path}")

    def load_policy(self, path: str) -> None:
        """Load policy from file."""
        with open(path, 'r') as f:
            policy_data = json.load(f)

        self.algorithm = RLAlgorithm(policy_data["algorithm"])
        self.total_steps = policy_data.get("total_steps", 0)

        if self.algorithm == RLAlgorithm.Q_LEARNING and "q_table" in policy_data:
            self.q_agent.q_table = {k: np.array(v) for k, v in policy_data["q_table"].items()}
            self.q_agent.epsilon = policy_data.get("epsilon", 0.1)

        logger.info(f"Policy loaded from {path}")


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_rl_engine(
    actions: List[str],
    algorithm: str = "q_learning",
    reward_type: str = "task_success"
) -> ReinforcementLearningEngine:
    """
    Factory function to create RL engine.

    Args:
        actions: List of action names
        algorithm: Algorithm name
        reward_type: Reward function type

    Returns:
        Configured RL engine
    """
    # Create action objects
    action_objects = [Action(id=f"action_{i}", name=name) for i, name in enumerate(actions)]

    # Create reward function
    if reward_type == "task_success":
        reward_fn = TaskSuccessReward()
    elif reward_type == "efficiency":
        reward_fn = EfficiencyReward()
    elif reward_type == "curiosity":
        reward_fn = CuriosityReward()
    else:
        reward_fn = CompositeReward([
            (TaskSuccessReward(), 0.5),
            (EfficiencyReward(), 0.3),
            (CuriosityReward(), 0.2)
        ])

    # Create engine
    return ReinforcementLearningEngine(
        actions=action_objects,
        algorithm=RLAlgorithm(algorithm),
        reward_function=reward_fn
    )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    "RLAlgorithm",
    "RewardType",
    "ExplorationStrategy",

    # Data classes
    "State",
    "Action",
    "Experience",
    "Policy",

    # Reward functions
    "RewardFunction",
    "TaskSuccessReward",
    "EfficiencyReward",
    "CuriosityReward",
    "CompositeReward",

    # Agents
    "MultiArmedBandit",
    "QLearningAgent",
    "PolicyGradientAgent",
    "ActorCriticAgent",
    "ContextualBandit",

    # Core
    "ExperienceReplayBuffer",
    "ReinforcementLearningEngine",
    "create_rl_engine"
]
