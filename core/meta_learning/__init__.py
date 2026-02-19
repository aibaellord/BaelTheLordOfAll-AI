# BAEL - Meta Learning System
# "Learning How to Learn"

"""
Meta Learning System - Continuously improves its own learning strategies.

This module provides adaptive learning capabilities:
- 8 learning strategies from supervised to adversarial
- Strategy selection optimization with exploration/exploitation
- Skill tracking with decay modeling
- Cross-domain knowledge transfer
- Experience banking and pattern detection

Usage:
    from core.meta_learning import MetaLearningSystem, LearningStrategy

    system = await MetaLearningSystem.create()
    best_strategy = await system.get_best_strategy(
        task="code_review",
        exploration_rate=0.1
    )
"""

from .meta_learning_system import (
    MetaLearningSystem,
    LearningStrategy,
    Experience,
    Outcome,
    SkillLevel,
    LearningGoal,
    ExperienceBank,
    PatternDetector,
    StrategyOptimizer,
    KnowledgeTransfer,
)

__all__ = [
    "MetaLearningSystem",
    "LearningStrategy",
    "Experience",
    "Outcome",
    "SkillLevel",
    "LearningGoal",
    "ExperienceBank",
    "PatternDetector",
    "StrategyOptimizer",
    "KnowledgeTransfer",
]
