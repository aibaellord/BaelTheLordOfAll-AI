# BAEL - Dream Mode Engine
# "Creative Exploration Beyond Constraints"

"""
Dream Mode Engine - Generates creative solutions through "dreaming".

This module enables creative exploration:
- 8 dream states from AWAKE to TRANSCENDENT
- 10 dream themes for different creative directions
- Lucid dreaming for goal-focused creativity
- Nightmare mode for failure exploration
- Sacred geometry integration for aesthetic coherence

Usage:
    from core.dream_mode import DreamModeEngine, DreamState, DreamTheme

    engine = await DreamModeEngine.create()
    sequence = await engine.dream(
        seed_idea="microservice architecture",
        target_state=DreamState.REM,
        theme=DreamTheme.FUSION
    )
"""

from .dream_mode_engine import (
    DreamModeEngine,
    DreamState,
    DreamTheme,
    DreamFragment,
    DreamInsight,
    DreamSequence,
    NightmareSeverity,
)

__all__ = [
    "DreamModeEngine",
    "DreamState",
    "DreamTheme",
    "DreamFragment",
    "DreamInsight",
    "DreamSequence",
    "NightmareSeverity",
]
