"""
BAEL World Model Engine
========================

Model-based reinforcement learning.
Learning and using world models.

"Ba'el models the world." — Ba'el
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

logger = logging.getLogger("BAEL.WorldModel")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ModelType(Enum):
    """Types of world models."""
    TABULAR = auto()       # State-action tables
    LINEAR = auto()        # Linear dynamics
    NEURAL = auto()        # Neural network (simulated)
    GAUSSIAN = auto()      # Gaussian process


class PlanningMethod(Enum):
    """Planning methods."""
    RANDOM_SHOOTING = auto()
    CROSS_ENTROPY = auto()
    MCTS = auto()
    MPPI = auto()


class UncertaintyType(Enum):
    """Types of uncertainty."""
    ALEATORIC = auto()     # Inherent randomness
    EPISTEMIC = auto()     # Model uncertainty


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
    name: str
    value: Any = None


@dataclass
class Transition:
    """
    A state transition.
    """
    state: State
    action: Action
    next_state: State
    reward: float
    done: bool
    probability: float = 1.0


@dataclass
class WorldModelPrediction:
    """
    World model prediction.
    """
    predicted_state: Dict[str, float]
    predicted_reward: float
    uncertainty: float
    done_probability: float


@dataclass
class SimulatedTrajectory:
    """
    A simulated trajectory.
    """
    states: List[State]
    actions: List[Action]
    rewards: List[float]
    total_reward: float
    length: int


@dataclass
class PlanResult:
    """
    Result of planning.
    """
    best_actions: List[Action]
    expected_reward: float
    trajectories_sampled: int
    planning_time: float


# ============================================================================
# TRANSITION MODEL
# ============================================================================

class TransitionModel:
    """
    Learn state transition dynamics.

    "Ba'el predicts transitions." — Ba'el
    """

    def __init__(
        self,
        model_type: ModelType = ModelType.TABULAR
    ):
        """Initialize model."""
        self._model_type = model_type

        # Tabular model: (state_key, action) -> [(next_state, prob)]
        self._transitions: Dict[Tuple[str, str], List[Tuple[Dict[str, float], float]]] = defaultdict(list)

        # Linear model: feature weights
        self._weights: Dict[str, Dict[str, Dict[str, float]]] = {}  # action -> feature -> delta

        self._update_count = 0
        self._lock = threading.RLock()

    def _state_key(self, state: State) -> str:
        """Create state key."""
        features = sorted(state.features.items())
        return str([(k, round(v, 2)) for k, v in features])

    def update(
        self,
        state: State,
        action: Action,
        next_state: State
    ) -> None:
        """Update model with transition."""
        with self._lock:
            self._update_count += 1

            if self._model_type == ModelType.TABULAR:
                key = (self._state_key(state), action.name)

                # Add or update transition
                self._transitions[key].append((next_state.features.copy(), 1.0))

            elif self._model_type == ModelType.LINEAR:
                # Learn linear dynamics
                if action.name not in self._weights:
                    self._weights[action.name] = defaultdict(lambda: defaultdict(float))

                # Update weights based on delta
                for feat, val in state.features.items():
                    delta = next_state.features.get(feat, 0) - val

                    # Simple learning rule
                    lr = 0.1
                    current = self._weights[action.name][feat].get(feat, 0)
                    self._weights[action.name][feat][feat] = current + lr * (delta - current)

    def predict(
        self,
        state: State,
        action: Action
    ) -> Tuple[Dict[str, float], float]:
        """Predict next state."""
        with self._lock:
            if self._model_type == ModelType.TABULAR:
                key = (self._state_key(state), action.name)

                transitions = self._transitions.get(key, [])

                if not transitions:
                    # Default: same state
                    return state.features.copy(), 1.0

                # Sample from observed transitions
                next_features, _ = random.choice(transitions)

                # Uncertainty from diversity
                uncertainty = 1.0 if len(transitions) <= 1 else 1.0 / math.sqrt(len(transitions))

                return next_features.copy(), uncertainty

            elif self._model_type == ModelType.LINEAR:
                next_features = state.features.copy()

                if action.name in self._weights:
                    for feat, val in state.features.items():
                        delta = self._weights[action.name][feat].get(feat, 0)
                        next_features[feat] = val + delta

                uncertainty = 1.0 / math.sqrt(1 + self._update_count)

                return next_features, uncertainty

            return state.features.copy(), 1.0


# ============================================================================
# REWARD MODEL
# ============================================================================

class RewardModel:
    """
    Learn reward function.

    "Ba'el predicts rewards." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # (state_key, action) -> [rewards]
        self._rewards: Dict[Tuple[str, str], List[float]] = defaultdict(list)
        self._lock = threading.RLock()

    def _state_key(self, state: State) -> str:
        features = sorted(state.features.items())
        return str([(k, round(v, 2)) for k, v in features])

    def update(
        self,
        state: State,
        action: Action,
        reward: float
    ) -> None:
        """Update reward model."""
        with self._lock:
            key = (self._state_key(state), action.name)
            self._rewards[key].append(reward)

    def predict(
        self,
        state: State,
        action: Action
    ) -> Tuple[float, float]:
        """Predict reward."""
        with self._lock:
            key = (self._state_key(state), action.name)

            rewards = self._rewards.get(key, [])

            if not rewards:
                return 0.0, 1.0  # Unknown

            mean = sum(rewards) / len(rewards)

            if len(rewards) == 1:
                uncertainty = 1.0
            else:
                variance = sum((r - mean) ** 2 for r in rewards) / len(rewards)
                uncertainty = math.sqrt(variance)

            return mean, uncertainty


# ============================================================================
# PLANNING
# ============================================================================

class ModelBasedPlanner:
    """
    Plan using world model.

    "Ba'el plans ahead." — Ba'el
    """

    def __init__(
        self,
        transition_model: TransitionModel,
        reward_model: RewardModel,
        actions: List[Action],
        horizon: int = 10,
        discount: float = 0.99
    ):
        """Initialize planner."""
        self._transition = transition_model
        self._reward = reward_model
        self._actions = actions
        self._horizon = horizon
        self._discount = discount
        self._lock = threading.RLock()

    def simulate_trajectory(
        self,
        start_state: State,
        action_sequence: List[Action]
    ) -> SimulatedTrajectory:
        """Simulate trajectory using model."""
        with self._lock:
            states = [start_state]
            rewards = []
            total_reward = 0.0
            discount = 1.0

            current_features = start_state.features.copy()

            for action in action_sequence:
                # Create state
                current_state = State(
                    id=f"sim_{len(states)}",
                    features=current_features
                )

                # Predict next state
                next_features, _ = self._transition.predict(current_state, action)

                # Predict reward
                reward, _ = self._reward.predict(current_state, action)

                rewards.append(reward)
                total_reward += discount * reward
                discount *= self._discount

                # Next state
                next_state = State(
                    id=f"sim_{len(states)}",
                    features=next_features
                )
                states.append(next_state)

                current_features = next_features

            return SimulatedTrajectory(
                states=states,
                actions=action_sequence,
                rewards=rewards,
                total_reward=total_reward,
                length=len(action_sequence)
            )

    def random_shooting(
        self,
        state: State,
        num_samples: int = 100
    ) -> PlanResult:
        """Plan using random shooting."""
        with self._lock:
            start_time = time.time()

            best_actions = None
            best_reward = float('-inf')

            for _ in range(num_samples):
                # Random action sequence
                actions = [random.choice(self._actions) for _ in range(self._horizon)]

                # Simulate
                trajectory = self.simulate_trajectory(state, actions)

                if trajectory.total_reward > best_reward:
                    best_reward = trajectory.total_reward
                    best_actions = actions

            return PlanResult(
                best_actions=best_actions or [],
                expected_reward=best_reward,
                trajectories_sampled=num_samples,
                planning_time=time.time() - start_time
            )

    def cross_entropy_method(
        self,
        state: State,
        num_samples: int = 100,
        elite_frac: float = 0.1,
        iterations: int = 5
    ) -> PlanResult:
        """Plan using Cross-Entropy Method."""
        with self._lock:
            start_time = time.time()

            # Initialize action probabilities
            n_actions = len(self._actions)
            probs = [[1.0/n_actions] * n_actions for _ in range(self._horizon)]

            total_sampled = 0

            for _ in range(iterations):
                trajectories = []

                for _ in range(num_samples):
                    # Sample action sequence from distribution
                    actions = []
                    for t in range(self._horizon):
                        idx = random.choices(range(n_actions), weights=probs[t])[0]
                        actions.append(self._actions[idx])

                    trajectory = self.simulate_trajectory(state, actions)
                    trajectories.append((trajectory, actions))
                    total_sampled += 1

                # Select elite
                trajectories.sort(key=lambda x: x[0].total_reward, reverse=True)
                elite_count = max(1, int(num_samples * elite_frac))
                elite = trajectories[:elite_count]

                # Update probabilities
                for t in range(self._horizon):
                    counts = [0] * n_actions
                    for traj, actions in elite:
                        idx = self._actions.index(actions[t])
                        counts[idx] += 1

                    total = sum(counts)
                    if total > 0:
                        probs[t] = [(c + 0.1) / (total + 0.1 * n_actions) for c in counts]

            # Best actions
            best_actions = [
                self._actions[probs[t].index(max(probs[t]))]
                for t in range(self._horizon)
            ]

            # Evaluate best
            best_traj = self.simulate_trajectory(state, best_actions)

            return PlanResult(
                best_actions=best_actions,
                expected_reward=best_traj.total_reward,
                trajectories_sampled=total_sampled,
                planning_time=time.time() - start_time
            )


# ============================================================================
# WORLD MODEL ENGINE
# ============================================================================

class WorldModelEngine:
    """
    Complete world model engine.

    "Ba'el's model of reality." — Ba'el
    """

    def __init__(
        self,
        actions: List[str],
        model_type: ModelType = ModelType.TABULAR,
        horizon: int = 10
    ):
        """Initialize engine."""
        self._action_names = actions
        self._actions = [Action(id=f"act_{i}", name=a) for i, a in enumerate(actions)]

        self._transition = TransitionModel(model_type)
        self._reward = RewardModel()
        self._planner = ModelBasedPlanner(
            self._transition, self._reward, self._actions, horizon
        )

        self._experience: List[Transition] = []
        self._state_counter = 0
        self._lock = threading.RLock()

    def _generate_state_id(self) -> str:
        self._state_counter += 1
        return f"state_{self._state_counter}"

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

    def get_action(self, name: str) -> Optional[Action]:
        """Get action by name."""
        for action in self._actions:
            if action.name == name:
                return action
        return None

    # Learning

    def observe(
        self,
        state: State,
        action_name: str,
        reward: float,
        next_state: State,
        done: bool
    ) -> None:
        """Observe transition and update model."""
        with self._lock:
            action = self.get_action(action_name)
            if not action:
                return

            # Update models
            self._transition.update(state, action, next_state)
            self._reward.update(state, action, reward)

            # Store experience
            self._experience.append(Transition(
                state=state,
                action=action,
                next_state=next_state,
                reward=reward,
                done=done
            ))

    # Prediction

    def predict_next(
        self,
        state: State,
        action_name: str
    ) -> WorldModelPrediction:
        """Predict next state."""
        action = self.get_action(action_name)
        if not action:
            return WorldModelPrediction(
                predicted_state={},
                predicted_reward=0.0,
                uncertainty=1.0,
                done_probability=0.0
            )

        next_features, trans_uncertainty = self._transition.predict(state, action)
        reward, reward_uncertainty = self._reward.predict(state, action)

        return WorldModelPrediction(
            predicted_state=next_features,
            predicted_reward=reward,
            uncertainty=(trans_uncertainty + reward_uncertainty) / 2,
            done_probability=0.0
        )

    # Planning

    def plan(
        self,
        state: State,
        method: PlanningMethod = PlanningMethod.RANDOM_SHOOTING,
        num_samples: int = 100
    ) -> PlanResult:
        """Plan from state."""
        if method == PlanningMethod.RANDOM_SHOOTING:
            return self._planner.random_shooting(state, num_samples)
        elif method == PlanningMethod.CROSS_ENTROPY:
            return self._planner.cross_entropy_method(state, num_samples)
        else:
            return self._planner.random_shooting(state, num_samples)

    def act(
        self,
        state: State,
        num_samples: int = 100
    ) -> str:
        """Get best action for state."""
        plan = self.plan(state, num_samples=num_samples)
        if plan.best_actions:
            return plan.best_actions[0].name
        return self._action_names[0]

    # Simulation

    def simulate(
        self,
        state: State,
        actions: List[str]
    ) -> SimulatedTrajectory:
        """Simulate trajectory."""
        action_objs = [self.get_action(a) for a in actions]
        action_objs = [a for a in action_objs if a is not None]
        return self._planner.simulate_trajectory(state, action_objs)

    @property
    def experience_count(self) -> int:
        return len(self._experience)

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'actions': len(self._actions),
            'experience': len(self._experience),
            'model_updates': self._transition._update_count
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_world_model(
    actions: List[str],
    horizon: int = 10
) -> WorldModelEngine:
    """Create world model engine."""
    return WorldModelEngine(actions, horizon=horizon)


def plan_actions(
    state: Dict[str, float],
    actions: List[str],
    horizon: int = 5
) -> List[str]:
    """Quick planning."""
    engine = create_world_model(actions, horizon)
    s = engine.create_state(state)
    result = engine.plan(s)
    return [a.name for a in result.best_actions]
