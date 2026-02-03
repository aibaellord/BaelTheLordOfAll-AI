"""
Advanced Feedback Loop System for BAEL

User preferences learning, A/B testing, multi-armed bandits,
and reinforcement learning integration.
"""

import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class FeedbackType(Enum):
    """Types of user feedback."""
    EXPLICIT = "explicit"  # User directly rates
    IMPLICIT = "implicit"  # Inferred from behavior
    COMPARATIVE = "comparative"  # Preference between options
    CONTEXTUAL = "contextual"  # Context-specific feedback


@dataclass
class UserFeedback:
    """User feedback record."""
    feedback_id: str
    user_id: str
    item_id: str
    feedback_type: FeedbackType
    score: float  # 0-1 range
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    actionable: bool = True


class PreferenceModel:
    """Models user preferences."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.preferences: Dict[str, float] = {}
        self.feature_weights: Dict[str, float] = {}
        self.historical_feedback: List[UserFeedback] = []
        self.preference_decay_factor = 0.99  # Exponential decay

    def record_feedback(self, feedback: UserFeedback) -> None:
        """Record user feedback."""
        self.historical_feedback.append(feedback)
        self.update_preferences(feedback)

    def update_preferences(self, feedback: UserFeedback) -> None:
        """Update preference model based on feedback."""
        item = feedback.item_id
        current_pref = self.preferences.get(item, 0.5)

        # Update with decay
        self.preferences[item] = (current_pref * self.preference_decay_factor +
                                 feedback.score * (1 - self.preference_decay_factor))

    def get_predicted_score(self, item_id: str) -> float:
        """Predict score for item."""
        return self.preferences.get(item_id, 0.5)

    def get_recommendations(self, candidates: List[str], top_k: int = 5) -> List[Tuple[str, float]]:
        """Get recommendations for candidates."""
        scores = [(item, self.get_predicted_score(item)) for item in candidates]
        return sorted(scores, key=lambda x: x[1], reverse=True)[:top_k]

    def get_preference_summary(self) -> Dict[str, Any]:
        """Get preference summary."""
        return {
            "user_id": self.user_id,
            "total_feedback": len(self.historical_feedback),
            "top_preferences": sorted(self.preferences.items(),
                                     key=lambda x: x[1],
                                     reverse=True)[:5],
            "avg_score": sum(f.score for f in self.historical_feedback) / len(self.historical_feedback) if self.historical_feedback else 0
        }


class ABTestExperiment:
    """A/B testing experiment."""

    def __init__(self, experiment_id: str, variant_a: str, variant_b: str):
        self.experiment_id = experiment_id
        self.variant_a = variant_a
        self.variant_b = variant_b
        self.users_a: Dict[str, List[float]] = {}
        self.users_b: Dict[str, List[float]] = {}
        self.started_at = datetime.now()
        self.ended_at: Optional[datetime] = None

    def record_variant_a(self, user_id: str, metric: float) -> None:
        """Record metric for variant A."""
        if user_id not in self.users_a:
            self.users_a[user_id] = []
        self.users_a[user_id].append(metric)

    def record_variant_b(self, user_id: str, metric: float) -> None:
        """Record metric for variant B."""
        if user_id not in self.users_b:
            self.users_b[user_id] = []
        self.users_b[user_id].append(metric)

    def get_results(self) -> Dict[str, Any]:
        """Get A/B test results."""
        scores_a = [m for metrics in self.users_a.values() for m in metrics]
        scores_b = [m for metrics in self.users_b.values() for m in metrics]

        avg_a = sum(scores_a) / len(scores_a) if scores_a else 0
        avg_b = sum(scores_b) / len(scores_b) if scores_b else 0

        return {
            "experiment_id": self.experiment_id,
            "variant_a": {
                "name": self.variant_a,
                "users": len(self.users_a),
                "avg_score": avg_a
            },
            "variant_b": {
                "name": self.variant_b,
                "users": len(self.users_b),
                "avg_score": avg_b
            },
            "winner": self.variant_a if avg_a > avg_b else self.variant_b,
            "improvement": abs(avg_a - avg_b) / max(avg_a, avg_b, 0.001) * 100 if max(avg_a, avg_b) > 0 else 0
        }


class MultiArmedBandit:
    """Multi-armed bandit algorithm."""

    def __init__(self, arms: List[str], exploration_rate: float = 0.1):
        self.arms = arms
        self.exploration_rate = exploration_rate
        self.arm_rewards: Dict[str, List[float]] = {arm: [] for arm in arms}
        self.arm_counts: Dict[str, int] = {arm: 0 for arm in arms}

    def select_arm(self) -> str:
        """Select arm using epsilon-greedy strategy."""
        if random.random() < self.exploration_rate:
            # Explore: random arm
            return random.choice(self.arms)
        else:
            # Exploit: best arm so far
            avg_rewards = {
                arm: sum(self.arm_rewards[arm]) / len(self.arm_rewards[arm]) if self.arm_rewards[arm] else 0
                for arm in self.arms
            }
            return max(avg_rewards.items(), key=lambda x: x[1])[0]

    def record_reward(self, arm: str, reward: float) -> None:
        """Record reward for arm."""
        if arm in self.arms:
            self.arm_rewards[arm].append(reward)
            self.arm_counts[arm] += 1

    def get_arm_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all arms."""
        return {
            arm: {
                "count": self.arm_counts[arm],
                "avg_reward": sum(self.arm_rewards[arm]) / len(self.arm_rewards[arm]) if self.arm_rewards[arm] else 0,
                "total_reward": sum(self.arm_rewards[arm])
            }
            for arm in self.arms
        }


class ReinforcementLearner:
    """Basic reinforcement learning component."""

    def __init__(self, learning_rate: float = 0.1, discount_factor: float = 0.99):
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.q_values: Dict[str, Dict[str, float]] = {}
        self.experience_buffer: List[Tuple[str, str, float, str]] = []

    def get_action_value(self, state: str, action: str) -> float:
        """Get Q-value for state-action pair."""
        if state not in self.q_values:
            self.q_values[state] = {}
        return self.q_values[state].get(action, 0.0)

    def update_q_value(self, state: str, action: str, reward: float,
                      next_state: str, next_action: str) -> None:
        """Update Q-value using Q-learning."""
        if state not in self.q_values:
            self.q_values[state] = {}

        current_q = self.get_action_value(state, action)
        next_q = self.get_action_value(next_state, next_action)

        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * next_q - current_q
        )

        self.q_values[state][action] = new_q

        # Store experience
        self.experience_buffer.append((state, action, reward, next_state))

    def select_action(self, state: str, possible_actions: List[str],
                     epsilon: float = 0.1) -> str:
        """Select action using epsilon-greedy policy."""
        if random.random() < epsilon:
            return random.choice(possible_actions)

        if state not in self.q_values:
            return random.choice(possible_actions)

        q_values = {a: self.q_values[state].get(a, 0.0) for a in possible_actions}
        best_action = max(q_values.items(), key=lambda x: x[1])[0]
        return best_action


class AdvancedFeedbackLoopSystem:
    """Main feedback loop orchestrator."""

    def __init__(self):
        self.user_preferences: Dict[str, PreferenceModel] = {}
        self.experiments: Dict[str, ABTestExperiment] = {}
        self.bandits: Dict[str, MultiArmedBandit] = {}
        self.rl_learner = ReinforcementLearner()

    def get_user_preferences(self, user_id: str) -> PreferenceModel:
        """Get or create user preference model."""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = PreferenceModel(user_id)
        return self.user_preferences[user_id]

    def record_user_feedback(self, user_id: str, item_id: str, score: float,
                            feedback_type: FeedbackType = FeedbackType.EXPLICIT) -> None:
        """Record user feedback."""
        feedback = UserFeedback(
            feedback_id=f"feedback_{int(datetime.now().timestamp())}",
            user_id=user_id,
            item_id=item_id,
            feedback_type=feedback_type,
            score=score
        )

        pref_model = self.get_user_preferences(user_id)
        pref_model.record_feedback(feedback)

    def get_personalized_recommendations(self, user_id: str,
                                        candidates: List[str],
                                        top_k: int = 5) -> List[Tuple[str, float]]:
        """Get personalized recommendations."""
        pref_model = self.get_user_preferences(user_id)
        return pref_model.get_recommendations(candidates, top_k)

    def create_ab_test(self, experiment_id: str, variant_a: str, variant_b: str) -> ABTestExperiment:
        """Create A/B test."""
        experiment = ABTestExperiment(experiment_id, variant_a, variant_b)
        self.experiments[experiment_id] = experiment
        return experiment

    def create_bandit(self, bandit_id: str, arms: List[str]) -> MultiArmedBandit:
        """Create multi-armed bandit."""
        bandit = MultiArmedBandit(arms)
        self.bandits[bandit_id] = bandit
        return bandit

    def get_system_stats(self) -> Dict[str, Any]:
        """Get feedback loop statistics."""
        return {
            "users": len(self.user_preferences),
            "experiments": len(self.experiments),
            "bandits": len(self.bandits),
            "rl_states": len(self.rl_learner.q_values),
            "total_experiences": len(self.rl_learner.experience_buffer),
            "timestamp": datetime.now().isoformat()
        }


# Global instance
_feedback_loop = None


def get_feedback_loop_system() -> AdvancedFeedbackLoopSystem:
    """Get or create global feedback loop system."""
    global _feedback_loop
    if _feedback_loop is None:
        _feedback_loop = AdvancedFeedbackLoopSystem()
    return _feedback_loop
