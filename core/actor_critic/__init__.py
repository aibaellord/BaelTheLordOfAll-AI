"""
BAEL Actor-Critic Engine
=========================

Reinforcement learning with value and policy.
Actor-critic methods.

"Ba'el learns to act and judge." — Ba'el
"""

import logging
import threading
import time
import math
import random
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
from collections import defaultdict, deque
import copy

logger = logging.getLogger("BAEL.ActorCritic")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class AlgorithmType(Enum):
    """Actor-critic algorithms."""
    A2C = auto()          # Advantage Actor-Critic
    A3C = auto()          # Asynchronous A3C
    PPO = auto()          # Proximal Policy Optimization
    SAC = auto()          # Soft Actor-Critic
    DDPG = auto()         # Deep Deterministic Policy Gradient


class UpdateMode(Enum):
    """Update mode."""
    ONLINE = auto()       # Update every step
    BATCH = auto()        # Update on batches
    EPISODIC = auto()     # Update after episodes


@dataclass
class State:
    """
    Environment state.
    """
    id: str
    features: Dict[str, float]
    terminal: bool = False


@dataclass
class Action:
    """
    An action.
    """
    id: str
    value: Any
    continuous: bool = False


@dataclass
class Transition:
    """
    A transition tuple.
    """
    state: State
    action: Action
    reward: float
    next_state: State
    done: bool
    timestamp: float = field(default_factory=time.time)


@dataclass
class PolicyOutput:
    """
    Policy network output.
    """
    action_probs: Dict[str, float]  # Action -> probability
    selected_action: str
    entropy: float


@dataclass
class ValueOutput:
    """
    Value network output.
    """
    state_value: float
    advantage: Optional[float] = None


@dataclass
class LearningStats:
    """
    Learning statistics.
    """
    policy_loss: float = 0.0
    value_loss: float = 0.0
    entropy: float = 0.0
    total_reward: float = 0.0
    episode_length: int = 0


# ============================================================================
# ACTOR (POLICY)
# ============================================================================

class Actor:
    """
    Actor network (policy).

    "Ba'el selects actions." — Ba'el
    """

    def __init__(
        self,
        actions: List[str],
        learning_rate: float = 0.001
    ):
        """Initialize actor."""
        self._actions = actions
        self._learning_rate = learning_rate

        # Simple policy: state features -> action preferences
        self._weights: Dict[str, Dict[str, float]] = {
            action: defaultdict(float)
            for action in actions
        }

        self._lock = threading.RLock()

    def forward(
        self,
        state: State,
        temperature: float = 1.0
    ) -> PolicyOutput:
        """Forward pass through policy."""
        with self._lock:
            # Compute action preferences
            preferences = {}

            for action in self._actions:
                pref = sum(
                    self._weights[action].get(feat, 0.0) * val
                    for feat, val in state.features.items()
                )
                preferences[action] = pref

            # Softmax with temperature
            max_pref = max(preferences.values())
            exp_prefs = {
                a: math.exp((p - max_pref) / temperature)
                for a, p in preferences.items()
            }
            total = sum(exp_prefs.values())

            probs = {a: e / total for a, e in exp_prefs.items()}

            # Sample action
            r = random.random()
            cumulative = 0.0
            selected = self._actions[0]

            for action, prob in probs.items():
                cumulative += prob
                if r <= cumulative:
                    selected = action
                    break

            # Compute entropy
            entropy = -sum(
                p * math.log(p + 1e-10) for p in probs.values()
            )

            return PolicyOutput(
                action_probs=probs,
                selected_action=selected,
                entropy=entropy
            )

    def update(
        self,
        state: State,
        action: str,
        advantage: float
    ) -> float:
        """Update policy using advantage."""
        with self._lock:
            # Policy gradient update
            policy = self.forward(state)

            for feat, val in state.features.items():
                # Increase probability of good actions
                for a in self._actions:
                    if a == action:
                        self._weights[a][feat] += (
                            self._learning_rate * advantage * val * (1 - policy.action_probs[a])
                        )
                    else:
                        self._weights[a][feat] -= (
                            self._learning_rate * advantage * val * policy.action_probs[a]
                        )

            # Return loss (negative log prob * advantage)
            return -math.log(policy.action_probs[action] + 1e-10) * advantage

    def get_action(self, state: State) -> str:
        """Get action from policy."""
        return self.forward(state).selected_action


# ============================================================================
# CRITIC (VALUE)
# ============================================================================

class Critic:
    """
    Critic network (value function).

    "Ba'el judges states." — Ba'el
    """

    def __init__(
        self,
        learning_rate: float = 0.01
    ):
        """Initialize critic."""
        self._learning_rate = learning_rate

        # Simple value function: linear in features
        self._weights: Dict[str, float] = defaultdict(float)
        self._bias: float = 0.0

        self._lock = threading.RLock()

    def forward(
        self,
        state: State
    ) -> ValueOutput:
        """Compute state value."""
        with self._lock:
            value = self._bias

            for feat, val in state.features.items():
                value += self._weights.get(feat, 0.0) * val

            return ValueOutput(state_value=value)

    def update(
        self,
        state: State,
        target: float
    ) -> float:
        """Update value function."""
        with self._lock:
            current = self.forward(state).state_value

            # TD error
            error = target - current

            # Update weights
            for feat, val in state.features.items():
                self._weights[feat] += self._learning_rate * error * val

            self._bias += self._learning_rate * error

            # Return squared error
            return error ** 2

    def compute_advantage(
        self,
        state: State,
        reward: float,
        next_state: State,
        done: bool,
        gamma: float = 0.99
    ) -> float:
        """Compute advantage for state-action pair."""
        with self._lock:
            current_value = self.forward(state).state_value

            if done:
                target = reward
            else:
                next_value = self.forward(next_state).state_value
                target = reward + gamma * next_value

            advantage = target - current_value

            return advantage


# ============================================================================
# REPLAY BUFFER
# ============================================================================

class ReplayBuffer:
    """
    Experience replay buffer.

    "Ba'el remembers experiences." — Ba'el
    """

    def __init__(
        self,
        capacity: int = 10000
    ):
        """Initialize buffer."""
        self._capacity = capacity
        self._buffer: deque = deque(maxlen=capacity)
        self._lock = threading.RLock()

    def add(
        self,
        transition: Transition
    ) -> None:
        """Add transition to buffer."""
        with self._lock:
            self._buffer.append(transition)

    def sample(
        self,
        batch_size: int
    ) -> List[Transition]:
        """Sample batch from buffer."""
        with self._lock:
            if len(self._buffer) < batch_size:
                return list(self._buffer)

            return random.sample(list(self._buffer), batch_size)

    def clear(self) -> None:
        """Clear buffer."""
        self._buffer.clear()

    def __len__(self) -> int:
        return len(self._buffer)


# ============================================================================
# ACTOR-CRITIC ENGINE
# ============================================================================

class ActorCriticEngine:
    """
    Complete actor-critic engine.

    "Ba'el's policy learning." — Ba'el
    """

    def __init__(
        self,
        actions: List[str],
        algorithm: AlgorithmType = AlgorithmType.A2C,
        gamma: float = 0.99,
        actor_lr: float = 0.001,
        critic_lr: float = 0.01,
        entropy_coef: float = 0.01
    ):
        """Initialize engine."""
        self._actions = actions
        self._algorithm = algorithm
        self._gamma = gamma
        self._entropy_coef = entropy_coef

        self._actor = Actor(actions, actor_lr)
        self._critic = Critic(critic_lr)
        self._buffer = ReplayBuffer()

        self._episode_rewards: List[float] = []
        self._total_steps = 0
        self._state_counter = 0
        self._action_counter = 0

        self._lock = threading.RLock()

    def _generate_state_id(self) -> str:
        self._state_counter += 1
        return f"state_{self._state_counter}"

    def _generate_action_id(self) -> str:
        self._action_counter += 1
        return f"action_{self._action_counter}"

    # State/Action creation

    def create_state(
        self,
        features: Dict[str, float],
        terminal: bool = False
    ) -> State:
        """Create state."""
        return State(
            id=self._generate_state_id(),
            features=features,
            terminal=terminal
        )

    def create_action(
        self,
        value: Any
    ) -> Action:
        """Create action."""
        return Action(
            id=self._generate_action_id(),
            value=value
        )

    # Policy

    def act(
        self,
        state: State,
        explore: bool = True
    ) -> str:
        """Select action for state."""
        with self._lock:
            if explore:
                policy = self._actor.forward(state)
                return policy.selected_action
            else:
                # Greedy
                policy = self._actor.forward(state, temperature=0.01)
                return max(policy.action_probs, key=policy.action_probs.get)

    def get_policy(
        self,
        state: State
    ) -> Dict[str, float]:
        """Get action probabilities for state."""
        return self._actor.forward(state).action_probs

    def get_value(
        self,
        state: State
    ) -> float:
        """Get state value."""
        return self._critic.forward(state).state_value

    # Learning

    def step(
        self,
        state: State,
        action: str,
        reward: float,
        next_state: State,
        done: bool
    ) -> LearningStats:
        """Take learning step."""
        with self._lock:
            self._total_steps += 1

            # Store transition
            action_obj = Action(id=action, value=action)
            transition = Transition(
                state=state,
                action=action_obj,
                reward=reward,
                next_state=next_state,
                done=done
            )
            self._buffer.add(transition)

            # Compute advantage
            advantage = self._critic.compute_advantage(
                state, reward, next_state, done, self._gamma
            )

            # Update critic
            if done:
                target = reward
            else:
                target = reward + self._gamma * self._critic.forward(next_state).state_value

            value_loss = self._critic.update(state, target)

            # Update actor
            policy_loss = self._actor.update(state, action, advantage)

            # Entropy bonus
            policy = self._actor.forward(state)
            entropy = policy.entropy

            return LearningStats(
                policy_loss=policy_loss,
                value_loss=value_loss,
                entropy=entropy,
                total_reward=reward,
                episode_length=1
            )

    def batch_update(
        self,
        batch_size: int = 32
    ) -> LearningStats:
        """Update from replay buffer."""
        with self._lock:
            transitions = self._buffer.sample(batch_size)

            if not transitions:
                return LearningStats()

            total_policy_loss = 0.0
            total_value_loss = 0.0
            total_entropy = 0.0

            for trans in transitions:
                stats = self.step(
                    trans.state,
                    trans.action.id,
                    trans.reward,
                    trans.next_state,
                    trans.done
                )

                total_policy_loss += stats.policy_loss
                total_value_loss += stats.value_loss
                total_entropy += stats.entropy

            n = len(transitions)

            return LearningStats(
                policy_loss=total_policy_loss / n,
                value_loss=total_value_loss / n,
                entropy=total_entropy / n,
                episode_length=n
            )

    def episode_end(
        self,
        total_reward: float
    ) -> None:
        """Record episode end."""
        self._episode_rewards.append(total_reward)

    # Analysis

    def get_average_reward(
        self,
        last_n: int = 100
    ) -> float:
        """Get average episode reward."""
        if not self._episode_rewards:
            return 0.0

        rewards = self._episode_rewards[-last_n:]
        return sum(rewards) / len(rewards)

    @property
    def total_steps(self) -> int:
        return self._total_steps

    @property
    def episode_count(self) -> int:
        return len(self._episode_rewards)

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'algorithm': self._algorithm.name,
            'actions': len(self._actions),
            'total_steps': self._total_steps,
            'episodes': self.episode_count,
            'average_reward': self.get_average_reward(),
            'buffer_size': len(self._buffer)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_actor_critic(
    actions: List[str],
    algorithm: AlgorithmType = AlgorithmType.A2C
) -> ActorCriticEngine:
    """Create actor-critic engine."""
    return ActorCriticEngine(actions, algorithm)


def simple_policy_gradient(
    actions: List[str],
    episodes: int = 100
) -> Actor:
    """Simple policy gradient training."""
    actor = Actor(actions)
    # Would need environment for actual training
    return actor
