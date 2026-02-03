"""
BAEL - Reinforcement Learning Module
Advanced RL for adaptive decision-making.
"""

from .rl_engine import (  # Enums; Data classes; Reward functions; Agents; Core
    Action, ActorCriticAgent, CompositeReward, ContextualBandit,
    CuriosityReward, EfficiencyReward, Experience, ExperienceReplayBuffer,
    ExplorationStrategy, MultiArmedBandit, Policy, PolicyGradientAgent,
    QLearningAgent, ReinforcementLearningEngine, RewardFunction, RewardType,
    RLAlgorithm, State, TaskSuccessReward, create_rl_engine)

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
