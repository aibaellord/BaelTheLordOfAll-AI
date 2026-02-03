#!/usr/bin/env python3
"""
BAEL - Reward Manager
Advanced reward shaping and reinforcement signal management.

Features:
- Reward shaping
- Intrinsic rewards
- Extrinsic rewards
- Reward normalization
- Reward discounting
- Multi-objective rewards
- Reward attribution
- Reward history tracking
"""

import asyncio
import hashlib
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class RewardType(Enum):
    """Type of reward."""
    INTRINSIC = "intrinsic"
    EXTRINSIC = "extrinsic"
    SHAPED = "shaped"
    SPARSE = "sparse"
    DENSE = "dense"


class RewardSignal(Enum):
    """Reward signal direction."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class NormalizationType(Enum):
    """Reward normalization type."""
    NONE = "none"
    MINMAX = "minmax"
    ZSCORE = "zscore"
    RUNNING = "running"


class AggregationType(Enum):
    """Reward aggregation type."""
    SUM = "sum"
    MEAN = "mean"
    MAX = "max"
    WEIGHTED = "weighted"


class DiscountType(Enum):
    """Discount type."""
    CONSTANT = "constant"
    EXPONENTIAL = "exponential"
    HYPERBOLIC = "hyperbolic"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class RewardSignalData:
    """Individual reward signal."""
    signal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    value: float = 0.0
    reward_type: RewardType = RewardType.EXTRINSIC
    signal: RewardSignal = RewardSignal.NEUTRAL
    source: str = ""
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RewardObjective:
    """Reward objective for multi-objective optimization."""
    objective_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    weight: float = 1.0
    target: float = 0.0
    current: float = 0.0
    priority: int = 0


@dataclass
class RewardShaper:
    """Reward shaping configuration."""
    shaper_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    potential_function: Optional[Callable[[Any], float]] = None
    discount: float = 0.99
    enabled: bool = True


@dataclass
class RewardStats:
    """Reward statistics."""
    count: int = 0
    total: float = 0.0
    mean: float = 0.0
    variance: float = 0.0
    min_value: float = float('inf')
    max_value: float = float('-inf')
    positive_count: int = 0
    negative_count: int = 0


@dataclass
class RewardAttribution:
    """Attribution of reward to actions."""
    attribution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action: str = ""
    contribution: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


# =============================================================================
# REWARD FUNCTIONS
# =============================================================================

class RewardFunction(ABC):
    """Abstract reward function."""

    @abstractmethod
    def compute(self, state: Any, action: Any, next_state: Any) -> float:
        """Compute reward."""
        pass


class ConstantReward(RewardFunction):
    """Constant reward function."""

    def __init__(self, value: float = 1.0):
        self._value = value

    def compute(self, state: Any, action: Any, next_state: Any) -> float:
        """Return constant reward."""
        return self._value


class DistanceReward(RewardFunction):
    """Distance-based reward function."""

    def __init__(self, goal: Any, scale: float = 1.0):
        self._goal = goal
        self._scale = scale

    def compute(self, state: Any, action: Any, next_state: Any) -> float:
        """Compute distance-based reward."""
        if isinstance(next_state, (int, float)) and isinstance(self._goal, (int, float)):
            distance = abs(next_state - self._goal)
            return -distance * self._scale
        return 0.0


class GoalReward(RewardFunction):
    """Goal-based reward function."""

    def __init__(self, goal: Any, reward: float = 10.0, penalty: float = -0.1):
        self._goal = goal
        self._reward = reward
        self._penalty = penalty

    def compute(self, state: Any, action: Any, next_state: Any) -> float:
        """Compute goal-based reward."""
        if next_state == self._goal:
            return self._reward
        return self._penalty


class CompositeReward(RewardFunction):
    """Composite reward from multiple functions."""

    def __init__(self):
        self._functions: List[Tuple[RewardFunction, float]] = []

    def add(self, func: RewardFunction, weight: float = 1.0) -> "CompositeReward":
        """Add reward function."""
        self._functions.append((func, weight))
        return self

    def compute(self, state: Any, action: Any, next_state: Any) -> float:
        """Compute composite reward."""
        total = 0.0
        for func, weight in self._functions:
            total += weight * func.compute(state, action, next_state)
        return total


class CallableReward(RewardFunction):
    """Reward from callable."""

    def __init__(self, fn: Callable[[Any, Any, Any], float]):
        self._fn = fn

    def compute(self, state: Any, action: Any, next_state: Any) -> float:
        """Compute using callable."""
        return self._fn(state, action, next_state)


# =============================================================================
# NORMALIZERS
# =============================================================================

class RewardNormalizer:
    """Normalize rewards."""

    def __init__(self, norm_type: NormalizationType = NormalizationType.RUNNING):
        self._type = norm_type
        self._mean = 0.0
        self._var = 1.0
        self._count = 0
        self._min = float('inf')
        self._max = float('-inf')

    def normalize(self, reward: float) -> float:
        """Normalize reward."""
        self._update_stats(reward)

        if self._type == NormalizationType.NONE:
            return reward

        elif self._type == NormalizationType.MINMAX:
            if self._max == self._min:
                return 0.0
            return (reward - self._min) / (self._max - self._min)

        elif self._type == NormalizationType.ZSCORE:
            std = math.sqrt(self._var) if self._var > 0 else 1.0
            return (reward - self._mean) / std

        elif self._type == NormalizationType.RUNNING:
            std = math.sqrt(self._var) if self._var > 0 else 1.0
            return reward / (std + 1e-8)

        return reward

    def _update_stats(self, reward: float) -> None:
        """Update running statistics."""
        self._count += 1
        self._min = min(self._min, reward)
        self._max = max(self._max, reward)

        # Welford's online algorithm
        delta = reward - self._mean
        self._mean += delta / self._count
        delta2 = reward - self._mean
        self._var = ((self._count - 1) * self._var + delta * delta2) / self._count


class RewardScaler:
    """Scale rewards."""

    def __init__(self, scale: float = 1.0, offset: float = 0.0):
        self._scale = scale
        self._offset = offset

    def scale(self, reward: float) -> float:
        """Scale reward."""
        return reward * self._scale + self._offset

    def clip(self, reward: float, min_val: float, max_val: float) -> float:
        """Clip reward to range."""
        return max(min_val, min(max_val, reward))


# =============================================================================
# DISCOUNTING
# =============================================================================

class RewardDiscounter:
    """Discount future rewards."""

    def __init__(
        self,
        gamma: float = 0.99,
        discount_type: DiscountType = DiscountType.EXPONENTIAL
    ):
        self._gamma = gamma
        self._type = discount_type

    def discount(self, rewards: List[float]) -> List[float]:
        """Compute discounted returns."""
        if not rewards:
            return []

        n = len(rewards)
        discounted = [0.0] * n

        # Work backwards
        running = 0.0
        for i in range(n - 1, -1, -1):
            if self._type == DiscountType.CONSTANT:
                running = rewards[i] + self._gamma * running

            elif self._type == DiscountType.EXPONENTIAL:
                running = rewards[i] + self._gamma * running

            elif self._type == DiscountType.HYPERBOLIC:
                # Hyperbolic discounting
                k = n - 1 - i
                discount_factor = 1 / (1 + self._gamma * k)
                running = rewards[i] + discount_factor * running

            discounted[i] = running

        return discounted

    def compute_return(self, rewards: List[float]) -> float:
        """Compute total discounted return."""
        discounted = self.discount(rewards)
        return discounted[0] if discounted else 0.0

    def compute_td_target(
        self,
        reward: float,
        next_value: float,
        done: bool = False
    ) -> float:
        """Compute TD target."""
        if done:
            return reward
        return reward + self._gamma * next_value


# =============================================================================
# INTRINSIC REWARDS
# =============================================================================

class IntrinsicRewardGenerator:
    """Generate intrinsic motivation rewards."""

    def __init__(self):
        self._visit_counts: Dict[str, int] = defaultdict(int)
        self._state_history: List[Any] = []

    def curiosity_reward(self, state: Any, prediction_error: float) -> float:
        """Compute curiosity-based intrinsic reward."""
        return prediction_error

    def novelty_reward(self, state: Any, beta: float = 0.1) -> float:
        """Compute novelty-based reward."""
        state_key = str(state)
        self._visit_counts[state_key] += 1
        count = self._visit_counts[state_key]

        return beta / math.sqrt(count)

    def count_based_reward(self, state: Any, beta: float = 1.0) -> float:
        """Compute count-based exploration bonus."""
        state_key = str(state)
        self._visit_counts[state_key] += 1
        count = self._visit_counts[state_key]

        return beta / count

    def empowerment_reward(self, n_actions: int, n_reachable: int) -> float:
        """Compute empowerment reward (simplified)."""
        if n_reachable <= 0:
            return 0.0

        return math.log(n_reachable) / math.log(max(n_actions, 2))

    def surprise_reward(self, expected_prob: float, actual: bool) -> float:
        """Compute surprise-based reward."""
        if actual:
            return -math.log(expected_prob + 1e-8)
        else:
            return -math.log(1 - expected_prob + 1e-8)


# =============================================================================
# REWARD SHAPING
# =============================================================================

class RewardShapingEngine:
    """Shape rewards using potential-based shaping."""

    def __init__(self, gamma: float = 0.99):
        self._gamma = gamma
        self._potential_functions: Dict[str, Callable[[Any], float]] = {}

    def add_potential(
        self,
        name: str,
        potential_fn: Callable[[Any], float]
    ) -> None:
        """Add potential function."""
        self._potential_functions[name] = potential_fn

    def shape(
        self,
        original_reward: float,
        state: Any,
        next_state: Any,
        potential_name: str = "default"
    ) -> float:
        """Shape reward using potential function."""
        if potential_name not in self._potential_functions:
            return original_reward

        phi = self._potential_functions[potential_name]

        # F(s, s') = γ * φ(s') - φ(s)
        shaping_reward = self._gamma * phi(next_state) - phi(state)

        return original_reward + shaping_reward

    def shape_all(
        self,
        original_reward: float,
        state: Any,
        next_state: Any
    ) -> float:
        """Apply all potential functions."""
        total_shaping = 0.0

        for name, phi in self._potential_functions.items():
            shaping = self._gamma * phi(next_state) - phi(state)
            total_shaping += shaping

        return original_reward + total_shaping


# =============================================================================
# MULTI-OBJECTIVE REWARDS
# =============================================================================

class MultiObjectiveRewardManager:
    """Manage multi-objective rewards."""

    def __init__(self, aggregation: AggregationType = AggregationType.WEIGHTED):
        self._objectives: Dict[str, RewardObjective] = {}
        self._aggregation = aggregation

    def add_objective(
        self,
        name: str,
        weight: float = 1.0,
        target: float = 0.0,
        priority: int = 0
    ) -> RewardObjective:
        """Add reward objective."""
        objective = RewardObjective(
            name=name,
            weight=weight,
            target=target,
            priority=priority
        )
        self._objectives[name] = objective
        return objective

    def update_objective(self, name: str, value: float) -> None:
        """Update objective value."""
        if name in self._objectives:
            self._objectives[name].current = value

    def compute_reward(
        self,
        objective_rewards: Dict[str, float]
    ) -> float:
        """Compute aggregated reward."""
        if not objective_rewards:
            return 0.0

        if self._aggregation == AggregationType.SUM:
            return sum(objective_rewards.values())

        elif self._aggregation == AggregationType.MEAN:
            return sum(objective_rewards.values()) / len(objective_rewards)

        elif self._aggregation == AggregationType.MAX:
            return max(objective_rewards.values())

        elif self._aggregation == AggregationType.WEIGHTED:
            total = 0.0
            weight_sum = 0.0

            for name, reward in objective_rewards.items():
                if name in self._objectives:
                    weight = self._objectives[name].weight
                    total += weight * reward
                    weight_sum += weight

            return total / weight_sum if weight_sum > 0 else 0.0

        return 0.0

    def get_pareto_rewards(
        self,
        objective_rewards: Dict[str, float]
    ) -> List[Tuple[str, float]]:
        """Get Pareto-sorted rewards."""
        sorted_objectives = sorted(
            objective_rewards.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_objectives


# =============================================================================
# REWARD BUFFER
# =============================================================================

class RewardBuffer:
    """Buffer for reward history."""

    def __init__(self, capacity: int = 10000):
        self._buffer: deque = deque(maxlen=capacity)
        self._stats = RewardStats()

    def add(self, reward: RewardSignalData) -> None:
        """Add reward to buffer."""
        self._buffer.append(reward)
        self._update_stats(reward.value)

    def add_value(
        self,
        value: float,
        source: str = "",
        reason: str = "",
        reward_type: RewardType = RewardType.EXTRINSIC
    ) -> RewardSignalData:
        """Add reward by value."""
        signal = (
            RewardSignal.POSITIVE if value > 0
            else RewardSignal.NEGATIVE if value < 0
            else RewardSignal.NEUTRAL
        )

        reward = RewardSignalData(
            value=value,
            reward_type=reward_type,
            signal=signal,
            source=source,
            reason=reason
        )

        self.add(reward)
        return reward

    def _update_stats(self, value: float) -> None:
        """Update statistics."""
        self._stats.count += 1
        self._stats.total += value

        # Update min/max
        self._stats.min_value = min(self._stats.min_value, value)
        self._stats.max_value = max(self._stats.max_value, value)

        # Update mean (running)
        delta = value - self._stats.mean
        self._stats.mean += delta / self._stats.count

        # Update variance (Welford)
        delta2 = value - self._stats.mean
        self._stats.variance = (
            (self._stats.count - 1) * self._stats.variance + delta * delta2
        ) / self._stats.count if self._stats.count > 0 else 0.0

        # Update counts
        if value > 0:
            self._stats.positive_count += 1
        elif value < 0:
            self._stats.negative_count += 1

    def get_recent(self, n: int = 10) -> List[RewardSignalData]:
        """Get recent rewards."""
        return list(self._buffer)[-n:]

    def get_stats(self) -> RewardStats:
        """Get reward statistics."""
        return self._stats

    def get_sum(self) -> float:
        """Get total sum."""
        return self._stats.total

    def get_mean(self) -> float:
        """Get mean reward."""
        return self._stats.mean

    def size(self) -> int:
        """Get buffer size."""
        return len(self._buffer)

    def clear(self) -> int:
        """Clear buffer."""
        count = len(self._buffer)
        self._buffer.clear()
        self._stats = RewardStats()
        return count


# =============================================================================
# REWARD ATTRIBUTION
# =============================================================================

class RewardAttributor:
    """Attribute rewards to actions."""

    def __init__(self, gamma: float = 0.99):
        self._gamma = gamma
        self._attributions: Dict[str, List[RewardAttribution]] = defaultdict(list)

    def attribute_immediate(
        self,
        action: str,
        reward: float
    ) -> RewardAttribution:
        """Attribute immediate reward."""
        attribution = RewardAttribution(
            action=action,
            contribution=reward
        )
        self._attributions[action].append(attribution)
        return attribution

    def attribute_delayed(
        self,
        action_sequence: List[str],
        final_reward: float
    ) -> List[RewardAttribution]:
        """Attribute delayed reward using discount."""
        attributions = []
        n = len(action_sequence)

        for i, action in enumerate(reversed(action_sequence)):
            discount_factor = self._gamma ** (n - 1 - i)
            contribution = final_reward * discount_factor

            attribution = RewardAttribution(
                action=action,
                contribution=contribution
            )

            attributions.append(attribution)
            self._attributions[action].append(attribution)

        return attributions

    def get_action_contribution(self, action: str) -> float:
        """Get total contribution of action."""
        if action not in self._attributions:
            return 0.0

        return sum(a.contribution for a in self._attributions[action])

    def get_top_actions(self, n: int = 5) -> List[Tuple[str, float]]:
        """Get top contributing actions."""
        contributions = [
            (action, self.get_action_contribution(action))
            for action in self._attributions.keys()
        ]

        contributions.sort(key=lambda x: x[1], reverse=True)
        return contributions[:n]


# =============================================================================
# REWARD MANAGER
# =============================================================================

class RewardManager:
    """
    Reward Manager for BAEL.

    Comprehensive reward management and shaping.
    """

    def __init__(
        self,
        gamma: float = 0.99,
        normalization: NormalizationType = NormalizationType.RUNNING
    ):
        self._gamma = gamma
        self._buffer = RewardBuffer()
        self._normalizer = RewardNormalizer(normalization)
        self._scaler = RewardScaler()
        self._discounter = RewardDiscounter(gamma)
        self._intrinsic = IntrinsicRewardGenerator()
        self._shaper = RewardShapingEngine(gamma)
        self._multi_objective = MultiObjectiveRewardManager()
        self._attributor = RewardAttributor(gamma)
        self._reward_functions: Dict[str, RewardFunction] = {}

    # -------------------------------------------------------------------------
    # REWARD SIGNALS
    # -------------------------------------------------------------------------

    def add_reward(
        self,
        value: float,
        source: str = "",
        reason: str = "",
        reward_type: RewardType = RewardType.EXTRINSIC
    ) -> RewardSignalData:
        """Add reward signal."""
        return self._buffer.add_value(value, source, reason, reward_type)

    def add_intrinsic_reward(
        self,
        value: float,
        source: str = "",
        reason: str = ""
    ) -> RewardSignalData:
        """Add intrinsic reward."""
        return self.add_reward(value, source, reason, RewardType.INTRINSIC)

    def add_extrinsic_reward(
        self,
        value: float,
        source: str = "",
        reason: str = ""
    ) -> RewardSignalData:
        """Add extrinsic reward."""
        return self.add_reward(value, source, reason, RewardType.EXTRINSIC)

    # -------------------------------------------------------------------------
    # REWARD FUNCTIONS
    # -------------------------------------------------------------------------

    def register_reward_function(
        self,
        name: str,
        func: RewardFunction
    ) -> None:
        """Register reward function."""
        self._reward_functions[name] = func

    def compute_reward(
        self,
        name: str,
        state: Any,
        action: Any,
        next_state: Any
    ) -> float:
        """Compute reward using registered function."""
        if name not in self._reward_functions:
            return 0.0

        return self._reward_functions[name].compute(state, action, next_state)

    def compute_all_rewards(
        self,
        state: Any,
        action: Any,
        next_state: Any
    ) -> Dict[str, float]:
        """Compute all registered rewards."""
        return {
            name: func.compute(state, action, next_state)
            for name, func in self._reward_functions.items()
        }

    # -------------------------------------------------------------------------
    # NORMALIZATION AND SCALING
    # -------------------------------------------------------------------------

    def normalize(self, reward: float) -> float:
        """Normalize reward."""
        return self._normalizer.normalize(reward)

    def scale(
        self,
        reward: float,
        scale: float = 1.0,
        offset: float = 0.0
    ) -> float:
        """Scale reward."""
        self._scaler._scale = scale
        self._scaler._offset = offset
        return self._scaler.scale(reward)

    def clip(self, reward: float, min_val: float, max_val: float) -> float:
        """Clip reward."""
        return self._scaler.clip(reward, min_val, max_val)

    # -------------------------------------------------------------------------
    # DISCOUNTING
    # -------------------------------------------------------------------------

    def discount_rewards(self, rewards: List[float]) -> List[float]:
        """Compute discounted rewards."""
        return self._discounter.discount(rewards)

    def compute_return(self, rewards: List[float]) -> float:
        """Compute discounted return."""
        return self._discounter.compute_return(rewards)

    def td_target(
        self,
        reward: float,
        next_value: float,
        done: bool = False
    ) -> float:
        """Compute TD target."""
        return self._discounter.compute_td_target(reward, next_value, done)

    # -------------------------------------------------------------------------
    # INTRINSIC REWARDS
    # -------------------------------------------------------------------------

    def curiosity_reward(self, state: Any, prediction_error: float) -> float:
        """Compute curiosity reward."""
        return self._intrinsic.curiosity_reward(state, prediction_error)

    def novelty_reward(self, state: Any, beta: float = 0.1) -> float:
        """Compute novelty reward."""
        return self._intrinsic.novelty_reward(state, beta)

    def exploration_bonus(self, state: Any, beta: float = 1.0) -> float:
        """Compute count-based exploration bonus."""
        return self._intrinsic.count_based_reward(state, beta)

    # -------------------------------------------------------------------------
    # REWARD SHAPING
    # -------------------------------------------------------------------------

    def add_potential_function(
        self,
        name: str,
        potential_fn: Callable[[Any], float]
    ) -> None:
        """Add potential function for shaping."""
        self._shaper.add_potential(name, potential_fn)

    def shape_reward(
        self,
        reward: float,
        state: Any,
        next_state: Any,
        potential_name: str = "default"
    ) -> float:
        """Shape reward using potential function."""
        return self._shaper.shape(reward, state, next_state, potential_name)

    # -------------------------------------------------------------------------
    # MULTI-OBJECTIVE
    # -------------------------------------------------------------------------

    def add_objective(
        self,
        name: str,
        weight: float = 1.0,
        target: float = 0.0
    ) -> RewardObjective:
        """Add reward objective."""
        return self._multi_objective.add_objective(name, weight, target)

    def aggregate_objectives(
        self,
        objective_rewards: Dict[str, float]
    ) -> float:
        """Aggregate multi-objective rewards."""
        return self._multi_objective.compute_reward(objective_rewards)

    # -------------------------------------------------------------------------
    # ATTRIBUTION
    # -------------------------------------------------------------------------

    def attribute_reward(self, action: str, reward: float) -> RewardAttribution:
        """Attribute reward to action."""
        return self._attributor.attribute_immediate(action, reward)

    def attribute_delayed_reward(
        self,
        actions: List[str],
        reward: float
    ) -> List[RewardAttribution]:
        """Attribute delayed reward to action sequence."""
        return self._attributor.attribute_delayed(actions, reward)

    def get_action_contribution(self, action: str) -> float:
        """Get action contribution."""
        return self._attributor.get_action_contribution(action)

    def get_top_actions(self, n: int = 5) -> List[Tuple[str, float]]:
        """Get top contributing actions."""
        return self._attributor.get_top_actions(n)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> RewardStats:
        """Get reward statistics."""
        return self._buffer.get_stats()

    def get_total_reward(self) -> float:
        """Get total reward."""
        return self._buffer.get_sum()

    def get_mean_reward(self) -> float:
        """Get mean reward."""
        return self._buffer.get_mean()

    def get_recent_rewards(self, n: int = 10) -> List[RewardSignalData]:
        """Get recent rewards."""
        return self._buffer.get_recent(n)

    def clear_history(self) -> int:
        """Clear reward history."""
        return self._buffer.clear()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Reward Manager."""
    print("=" * 70)
    print("BAEL - REWARD MANAGER DEMO")
    print("Advanced Reward Shaping and Reinforcement Signals")
    print("=" * 70)
    print()

    manager = RewardManager(gamma=0.99)

    # 1. Add Basic Rewards
    print("1. ADD BASIC REWARDS:")
    print("-" * 40)

    r1 = manager.add_reward(1.0, "task", "completed task")
    r2 = manager.add_reward(-0.5, "action", "invalid action")
    r3 = manager.add_intrinsic_reward(0.1, "curiosity", "novel state")

    print(f"   Reward 1: {r1.value} ({r1.signal.value})")
    print(f"   Reward 2: {r2.value} ({r2.signal.value})")
    print(f"   Reward 3: {r3.value} ({r3.reward_type.value})")
    print()

    # 2. Register Reward Functions
    print("2. REWARD FUNCTIONS:")
    print("-" * 40)

    manager.register_reward_function("goal", GoalReward(goal=10, reward=10.0))
    manager.register_reward_function("distance", DistanceReward(goal=10, scale=0.1))
    manager.register_reward_function("constant", ConstantReward(value=-0.01))

    computed = manager.compute_reward("goal", state=5, action="move", next_state=10)
    print(f"   Goal reward (reached goal): {computed}")

    computed = manager.compute_reward("distance", state=5, action="move", next_state=8)
    print(f"   Distance reward (moved closer): {computed:.2f}")

    all_rewards = manager.compute_all_rewards(5, "move", 8)
    print(f"   All rewards: {all_rewards}")
    print()

    # 3. Normalization
    print("3. NORMALIZATION:")
    print("-" * 40)

    raw_rewards = [0.1, 0.5, 1.0, 2.0, 0.3]
    normalized = [manager.normalize(r) for r in raw_rewards]

    print(f"   Raw rewards: {raw_rewards}")
    print(f"   Normalized:  {[f'{n:.3f}' for n in normalized]}")
    print()

    # 4. Discounting
    print("4. DISCOUNTING:")
    print("-" * 40)

    episode_rewards = [0.1, 0.2, 0.3, 10.0]
    discounted = manager.discount_rewards(episode_rewards)
    total_return = manager.compute_return(episode_rewards)

    print(f"   Episode rewards: {episode_rewards}")
    print(f"   Discounted:      {[f'{d:.2f}' for d in discounted]}")
    print(f"   Total return:    {total_return:.2f}")
    print()

    # 5. TD Target
    print("5. TD TARGET:")
    print("-" * 40)

    reward = 1.0
    next_value = 5.0
    td_target = manager.td_target(reward, next_value, done=False)

    print(f"   Reward: {reward}")
    print(f"   Next value: {next_value}")
    print(f"   TD target (γ=0.99): {td_target:.2f}")
    print()

    # 6. Intrinsic Rewards
    print("6. INTRINSIC REWARDS:")
    print("-" * 40)

    novelty = manager.novelty_reward("new_state", beta=0.1)
    print(f"   Novelty reward (first visit): {novelty:.4f}")

    novelty2 = manager.novelty_reward("new_state", beta=0.1)
    print(f"   Novelty reward (second visit): {novelty2:.4f}")

    exploration = manager.exploration_bonus("another_state", beta=1.0)
    print(f"   Exploration bonus: {exploration:.4f}")
    print()

    # 7. Reward Shaping
    print("7. REWARD SHAPING:")
    print("-" * 40)

    # Add potential function (distance to goal)
    manager.add_potential_function(
        "goal_potential",
        lambda s: -abs(s - 10) if isinstance(s, (int, float)) else 0
    )

    original = 0.0
    shaped = manager.shape_reward(original, state=5, next_state=7, potential_name="goal_potential")

    print(f"   Original reward: {original}")
    print(f"   Shaped reward:   {shaped:.2f}")
    print(f"   (Moved from state 5 to 7, closer to goal 10)")
    print()

    # 8. Multi-Objective Rewards
    print("8. MULTI-OBJECTIVE REWARDS:")
    print("-" * 40)

    manager.add_objective("efficiency", weight=0.5)
    manager.add_objective("accuracy", weight=0.3)
    manager.add_objective("speed", weight=0.2)

    objective_rewards = {
        "efficiency": 0.8,
        "accuracy": 0.9,
        "speed": 0.7
    }

    aggregated = manager.aggregate_objectives(objective_rewards)

    print(f"   Efficiency: 0.8 (weight: 0.5)")
    print(f"   Accuracy:   0.9 (weight: 0.3)")
    print(f"   Speed:      0.7 (weight: 0.2)")
    print(f"   Aggregated: {aggregated:.3f}")
    print()

    # 9. Reward Attribution
    print("9. REWARD ATTRIBUTION:")
    print("-" * 40)

    manager.attribute_reward("action_a", 5.0)
    manager.attribute_reward("action_b", 3.0)
    manager.attribute_reward("action_a", 2.0)

    actions = ["move_1", "move_2", "move_3"]
    manager.attribute_delayed_reward(actions, 10.0)

    contribution_a = manager.get_action_contribution("action_a")
    top_actions = manager.get_top_actions(3)

    print(f"   action_a contribution: {contribution_a:.2f}")
    print(f"   Top actions: {top_actions}")
    print()

    # 10. Clipping
    print("10. CLIPPING:")
    print("-" * 40)

    clipped = manager.clip(100.0, min_val=-1.0, max_val=1.0)
    print(f"   Original: 100.0")
    print(f"   Clipped [-1, 1]: {clipped}")
    print()

    # 11. Scaling
    print("11. SCALING:")
    print("-" * 40)

    scaled = manager.scale(0.5, scale=10.0, offset=1.0)
    print(f"   Original: 0.5")
    print(f"   Scaled (10x + 1): {scaled}")
    print()

    # 12. Composite Rewards
    print("12. COMPOSITE REWARDS:")
    print("-" * 40)

    composite = CompositeReward()
    composite.add(ConstantReward(-0.01), weight=1.0)
    composite.add(DistanceReward(goal=10), weight=0.5)
    composite.add(GoalReward(goal=10, reward=10.0), weight=2.0)

    result = composite.compute(state=5, action="move", next_state=10)
    print(f"   Composite reward (goal reached): {result:.2f}")

    result = composite.compute(state=5, action="move", next_state=7)
    print(f"   Composite reward (progress): {result:.2f}")
    print()

    # 13. Statistics
    print("13. STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()

    print(f"   Total count: {stats.count}")
    print(f"   Total sum:   {stats.total:.2f}")
    print(f"   Mean:        {stats.mean:.4f}")
    print(f"   Min:         {stats.min_value:.2f}")
    print(f"   Max:         {stats.max_value:.2f}")
    print(f"   Positive:    {stats.positive_count}")
    print(f"   Negative:    {stats.negative_count}")
    print()

    # 14. Recent Rewards
    print("14. RECENT REWARDS:")
    print("-" * 40)

    recent = manager.get_recent_rewards(5)

    for r in recent[:5]:
        print(f"   {r.value:.2f} from {r.source or 'unknown'}")
    print()

    # 15. Clear History
    print("15. CLEAR HISTORY:")
    print("-" * 40)

    cleared = manager.clear_history()
    print(f"   Cleared {cleared} rewards")
    print(f"   Current count: {manager.get_stats().count}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Reward Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
